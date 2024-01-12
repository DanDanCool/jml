class EvalError(Exception):
    def __init__(self, message, token):
        self.message = message
        self.token = token

class EvalResult:
    def __init__(self, result, token, message):
        self.result = result
        self.tokens = [ token ]
        self.messages = [ message ]


# basic expression for some literal
class Expr:
    def __init__(self, token):
        self.token = token

    def evaluate(self, environment):
        raise EvalError('unknown expression type', self.token)


class IdentifierExpr(Expr):
    def __init__(self, token):
        super().__init__(token)

    def evaluate(self, environment):
        if self.token.data in environment:
            return environment[self.token.data]
        raise EvalError(f"literal '{self.token.data}' not defined", self.token)

    def identifier(self):
        return self.token.data


class NumberExpr(Expr):
    def __init__(self, token):
        super().__init__(token)
        self.message = ''

    def evaluate(self, environment):
        def consecutive_underscore(i, c, underscore, invalid):
            if c == '_':
                if underscore:
                    invalid.append(i)
                return True
            return False

        def show_errors(message, indices):
            data = ""
            for i, c in enumerate(message):
                if i in indices:
                    data += f" *{c}* "
                else:
                    data += c
            return data

        data = self.token.data
        valid = True

        if data[0:2].lower() == '0x':
            # hex
            valid_chars = 'abcdef_'
            invalid = []
            if data[2] == '_':
                valid = False
                invalid.append(2)

            underscore = False
            for i, c in enumerate(data[2:]):
                if not (c.isdecimal() or c.lower() in valid_chars):
                    invalid.append(i)
                    valid = False
                underscore = consecutive_underscore(i, c, underscore, invalid)
            if valid:
                return int(data, base=16)
            raise EvalError(f"invalid chars found in hex number: {show_errors(data, invalid)}", self.token)
        else:
            valid_chars = '_.e'
            invalid = []
            underscore = False
            dot = False
            e_index = -1

            for i, c in enumerate(data):
                if not (c.isdecimal() or c.lower() in valid_chars):
                    invalid.append(i)
                    valid = False
                underscore = consecutive_underscore(i, c, underscore, invalid)
                if c == '.':
                    if dot:
                        invalid.append(i)
                    if data[max(0, i - 1)] == '_':
                        invalid.append(i - 1)
                    if data[max(i + 1, len(data) - 1)] == '_':
                        invalid.append(i + 1)
                    dot = True
                if c == 'e':
                    e_index = i
                    break
            if e_index != -1:
                beg = e_index + 1 + (data[e_index + 1] in '-+')
                # unlike python we do not allow underscores in the e specifier
                for i, c in enumerate(data[beg:]):
                    if not c.isdecimal():
                        invalid.append(i)
                        valid = False
            if dot and len(data) == 1:
                valid = False
                invalid.append(0)
            if valid:
                return float(data)
            raise EvalError(f"invalid chars found in number: {show_errors(data, invalid)}", self.token)
        raise EvalError('unable to parse number', self.token)


class StringExpr(Expr):
    special = {
            'n': '\n',
            't': '\t',
            'r': '\r',
            }

    def __init__(self, token):
        super().__init__(token)

    def evaluate(self, environment):
        result = ''
        backslash = False
        valid = True

        data = self.token.data
        for i, c in enumerate(data[1:-1]):
            if backslash:
                if c in special:
                    result += special[c]
                else:
                    result += c
                backslash = False
            else:
                if c == '\\':
                    backslash = True
                else:
                    result += c
        if backslash:
            raise EvalError(f"unpaired '\\' at the end of string: {data}", self.token)
        return result


class BoolExpr(Expr):
    def __init__(self, token):
        super().__init__(token)

    def evaluate(self, environment):
        data = self.token.data
        result = None
        if data == 'true':
            return True
        elif data == 'false':
            return False
        raise EvalError(f"unknown boolean type: {data}", self.token)


class UnaryExpr(Expr):
    def __init__(self, token, expr):
        super().__init__(token)
        self.expr = expr

    def evaluate(self, environment):
        res = self.expr.evaluate(environment)
        op = self.token.data
        if (op in [ '+', '-' ] and type(res) not in [ int, float ]) or type(res) not in [ bool, int, float ]:
            raise EvalError(f"invalid attempt to perform {op} on {type(res)}", self.token)

        if op == '!':
            return not res
        elif op == '+':
            return +res
        elif op == '-':
            return -res
        raise EvalError(f"unknown unary operation {op}", self.token)


class GroupExpr(Expr):
    def __init__(self, token, expr):
        super().__init__(token)
        self.expr = expr

    def evaluate(self, environment):
        return self.expr.evaluate(environment)


class BinaryExpr(Expr):
    def __init__(self, token, left, right):
        super().__init__(token)
        self.left = left
        self.right = right
        self.err = None

    def evaluate_children(self, environment):
        left = None
        right = None
        errors = []
        try:
            left = self.left.evaluate(environment)
        except EvalError as err:
            errors.append(err)

        try:
            right = self.right.evaluate(environment)
        except EvalError as err:
            errors.append(err)

        if len(errors):
            raise ExceptionGroup('one or more errors occured when evaluated binary expression', errors)
        return (left, right)


class ArithmeticExpr(BinaryExpr):
    def __init__(self, token, left, right):
        super().__init__(token, left, right)

    def add(self, environment, left, right):
        if type(left) == str and type(right) == str:
            return left + right

        valid_types = [ int, float, bool ]
        if type(left) not in valid_types or type(right) not in valid_types:
            raise EvalError(f"invalid params, arithmetic operation '+' expects two numbers", self.token)

        return float(left) + float(right)

    def evaluate(self, environment):
        (left, right) = self.evaluate_children(environment)

        op = self.token.data
        if op == '+':
            return self.add(environment, left, right)

        valid_types = [ int, float, bool ]
        if type(left) not in valid_types or type(right) not in valid_types:
            raise EvalError(f"invalid params, arithmetic operation '{op}' expects two numbers", self.token)

        if op == '-':
            return float(left) - float(right)
        elif op == '*':
            return float(left) * float(right)
        elif op == '/':
            if float(right) == 0:
                raise EvalError('division by zero', self.token)
            return float(left) / float(right)

        raise EvalError(f"unknown arithmetic operation {op}", self.token)


class ComparisonExpr(BinaryExpr):
    def __init__(self, token, left, right):
        super().__init__(token, left, right)

    def evaluate(self, environment):
        (left, right) = self.evaluate_children(environment)

        op = self.token.data
        if type(left) != type(right):
            raise EvalError(f"invalid params, comparison '{op}' expects two params of the same type", self.token)

        if type(left) not in [ int, float, bool ]:
            raise EvalError(f"invalid params, comparison '{op}' expects two numbers or two bools", self.token)

        if op == '==':
            return left == right
        elif op == '!=':
            return left != right

        if type(left) not in [ int, float ]:
            raise EvalError(f"invalid params, comparison '{op}' expects two numbers", self.token)

        if op == '<=':
            return left <= right
        elif op == '>=':
            return left >= right
        elif op == '<':
            return left < right
        elif op == '>':
            return left > right

        raise EvalError(f"unknown comparison operator '{op}'", self.token)


class LogicExpr(BinaryExpr):
    def __init__(self, token, left, right):
        super().__init__(token, left, right)

    def evaluate(self, environment):
        (left, right) = self.evaluate_children(environment)

        valid_types = [ int, float, bool ]
        op = self.token.data
        if type(left) not in valid_types or type(right) not in valid_types:
            raise EvalError(f"invalid params, logic operator '{op}' expects two numbers or bools", self.token)

        if op == 'and':
            return bool(left) and bool(right)
        elif op == 'or':
            return bool(left) or bool(right)

        raise EvalError(f"unknown logic operator '{op}'", self.token)


class StatementExpr(Expr):
    def __init__(self, token, identifier, expr):
        super().__init__(token)
        self.identifier = identifier
        self.expr = expr

    def rvalue(self, environment):
        res = self.expr.evaluate(environment)
        environment[self.identifier.identifier()] = res
        return res

    def lvalue(self):
        return self.identifier.identifier()

    def evaluate(self, environment):
        return self.rvalue(environment)


class ArrayExpr(Expr):
    def __init__(self, token, exprs):
        super().__init__(token)
        self.exprs = exprs

    def evaluate(self, environment):
        res = []
        errs = []
        array_type = None
        for expr in self.exprs:
            tmp = None
            try:
                tmp = expr.evaluate(environment)
            except EvalError as err:
                errs.append(err)
            except ExceptionGroup as err:
                errs.extend(list(err.exceptions))

            if array_type:
                if type(tmp) != array_type:
                    errs.append(EvalError(f"error, element {expr.token} must match array type {array_type}"))
            else:
                array_type = type(tmp)
            res.append(tmp)

        if len(errs):
            raise ExceptionGroup('one or more errors found when evaluating array expression', errs)
        return res


class TableExpr(Expr):
    def __init__(self, token, statements):
        super().__init__(token)
        self.statements = statements

    def evaluate(self, environment):
        res = {}
        errs = []
        for statement in self.statements:
            try:
                res[statement.lvalue()] = statement.rvalue(environment)
            except EvalError as err:
                errs.append(err)
            except ExceptionGroup as err:
                errs.extend(list(err.exceptions))
        if len(errs):
            raise ExceptionGroup('one or more errors found when evaluating dictionary expression', errs)
        return res

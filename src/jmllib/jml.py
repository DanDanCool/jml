from enum import Enum
from . import expr

class ParseError(Exception):
    def __init__(self, message, token):
        self.message = message
        self.token = token

TokenType = Enum('TokenType', [
    # single character tokens
    'LPAREN', 'RPAREN', 'LCBRACE', 'RCBRACE', 'LBRACE', 'RBRACE',
    'COMMA', 'MINUS', 'PLUS', 'SLASH', 'STAR',

    # one or two character tokens
    'EQUAL', 'EQUAL_EQUAL', 'BANG', 'BANG_EQUAL', 'GREATER', 'GREATER_EQUAL',
    'LESS', 'LESS_EQUAL',

    # literals
    'IDENTIFIER', 'STRING', 'NUMBER',

    # keywords
    'AND', 'OR', 'TRUE', 'FALSE',

    # misc
    'COMMENT', 'EOF'
    ])


class Token:
    def __init__(self, tokentype, data, beg, end):
        self.tokentype = tokentype
        self.data = data[beg:end]
        self.beg = beg
        self.end = end


# return 0 indexed line and column numbers
def linecolumn(s, n):
    ln = s[0:n].count('\n')
    # note that this means that every column starts with \n
    col = n - s[0:n].rfind('\n')
    return (ln, col)


def getline(s, pos):
    return s.split('\n')[pos[0]]


class Tokenizer:
    single_character = {
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '{': TokenType.LCBRACE,
            '}': TokenType.RCBRACE,
            '[': TokenType.LBRACE,
            ']': TokenType.RBRACE,
            ',': TokenType.COMMA,
            '-': TokenType.MINUS,
            '+': TokenType.PLUS,
            '/': TokenType.SLASH,
            '*': TokenType.STAR
            }

    double_character = {
            '=': TokenType.EQUAL,
            '!': TokenType.BANG,
            '<': TokenType.LESS,
            '>': TokenType.GREATER,
            '==': TokenType.EQUAL_EQUAL,
            '!=': TokenType.BANG_EQUAL,
            '<=': TokenType.LESS_EQUAL,
            '>=': TokenType.GREATER_EQUAL
            }

    keywords = {
        'and': TokenType.AND,
        'or': TokenType.OR,
        'true': TokenType.TRUE,
        'false': TokenType.FALSE
            }

    def __init__(self):
        self.index = 0
        self.data = ''

    def eof(self):
        return len(self.data) <= self.index

    def consume(self):
        whitespace = [ ' ', '\t', '\n', '\r' ]
        c = ' '
        while c in whitespace:
            if self.eof():
                return TokenType.EOF
            c = self.data[self.index]
            self.index += 1
        return c

    def peek(self):
        if self.eof(): return TokenType.EOF
        return self.data[self.index]

    def tokenize(self, jml):
        self.index = 0
        self.data = jml

        tokens = []
        c = ''

        while c != TokenType.EOF:
            c = self.consume()
            if c == TokenType.EOF:
                pass
            elif c == '#':
                # skip the rest of the line
                while not self.eof() and self.data[self.index] != '\n':
                    self.index += 1
            elif c in Tokenizer.single_character:
                tokens.append(Token(Tokenizer.single_character[c], self.data, self.index - 1, self.index))
            elif c in Tokenizer.double_character:
                if self.peek() == '=':
                    self.consume()
                    tokens.append(Token(Tokenizer.double_character[c + '='], self.data, self.index - 2, self.index))
                else:
                    tokens.append(Token(Tokenizer.double_character[c], self.data, self.index - 1, self.index))
            elif c == '"':
                # handle strings
                beg = self.index - 1
                while not self.eof() and self.data[self.index] != '"':
                    self.index += 1
                self.index += 1
                tokens.append(Token(TokenType.STRING, self.data, beg, self.index))
            elif c.isdigit():
                # handle numbers
                beg = self.index - 1
                special = 'x_.abcdef'
                validchar = lambda c: c.isdigit() or (c.lower() in special)
                while not self.eof() and validchar(self.data[self.index]):
                    self.index += 1
                tokens.append(Token(TokenType.NUMBER, self.data, beg, self.index))
            else:
                # handle identifiers and keywords
                def accept(c):
                    special = [ '_' ]
                    return c.isalnum() or c in special
                beg = self.index - 1
                while not self.eof() and accept(self.data[self.index]):
                    self.index += 1
                s = self.data[beg:self.index]
                if s in Tokenizer.keywords:
                    tokens.append(Token(Tokenizer.keywords[s], self.data, beg, self.index))
                else:
                    tokens.append(Token(TokenType.IDENTIFIER, self.data, beg, self.index))

        tokens.append(Token(TokenType.EOF, self.data, 0, self.index))
        return tokens

    def pretty_print(self, tokens):
        for token in tokens:
            beg = linecolumn(self.data, token.beg)
            end = linecolumn(self.data, token.end)
            info = f"{token.tokentype} from ln {beg[0] + 1}, col {beg[1]} to ln {end[0] + 1} col {end[1]}:\t\t\t\t\t{token.data}"
            print(info)


class Parser:
    def __init__(self):
        self.index = 0
        self.tokens = []

    def eof(self, index=None):
        if not index:
            index = self.index
        # always an extra eof token at the end
        return (len(self.tokens) - 1) <= index

    def consume(self, token):
        if self.cur().tokentype != token:
            raise ParseError(f"expected '{token}', found '{self.cur().tokentype}'", self.cur())
        self.index += 1

    def match(self, token):
        return self.cur().tokentype == token

    def peek(self):
        if self.eof(self.index + 1):
            return TokenType.EOF
        return self.tokens[self.index + 1]

    def cur(self):
        return self.tokens[self.index]

    def next(self):
        self.index += 1

    def sync(self, identifier=False):
        while not self.eof() and not self.match(TokenType.IDENTIFIER):
            if not identifier and self.match(TokenType.COMMA):
                self.next()
                return
            self.next()

    def parse_expr(self, lexpr=None):
        left = None
        match self.cur().tokentype:
            case TokenType.IDENTIFIER:
                left = expr.IdentifierExpr(self.cur())
                self.next()
            case TokenType.STRING:
                left = expr.StringExpr(self.cur())
                self.next()
            case TokenType.NUMBER:
                left = expr.NumberExpr(self.cur())
                self.next()
            case TokenType.TRUE | TokenType.FALSE:
                left = expr.BoolExpr(self.cur())
                self.next()
            case TokenType.COMMA | TokenType.RPAREN:
                return None
            case TokenType.PLUS | TokenType.MINUS | TokenType.BANG:
                token = self.cur()
                self.next()
                right = self.parse_expr()
                if not right:
                    raise ParseError(f"unexpected token while parsing unary expression '{self.cur().tokentype}'", self.cur())
                left = expr.UnaryExpr(token, right)
            case TokenType.LPAREN:
                token = self.cur()
                self.next()
                right = self.parse_expr()
                if not right:
                    raise ParseError(f"unexpted token while parsing group expression '{self.cur().tokentype}'", self.cur())
                left = expr.GroupExpr(token, right)
                self.consume(TokenType.RPAREN)
            case _:
                raise ParseError(f"unexpected token while parsing expression '{self.cur().tokentype}'", self.cur())

        if lexpr:
            lexpr.right = left
            left = lexpr

        op = self.cur()
        right = None
        match op.tokentype:
            case TokenType.PLUS | TokenType.MINUS:
                self.next()
                right = self.parse_expr()
                return expr.ArithmeticExpr(op, left, right)
            case TokenType.EQUAL_EQUAL | TokenType.BANG_EQUAL | TokenType.GREATER | TokenType.GREATER_EQUAL | \
            TokenType.LESS | TokenType.LESS_EQUAL:
                self.next()
                right = self.parse_expr()
                return expr.ComparisonExpr(op, left, right)
            case TokenType.SLASH | TokenType.STAR:
                self.next()
                return self.parse_expr(lexpr=expr.ArithmeticExpr(op, left, None))
            case _:
                return left
        raise ParseError(f"unknown operation '{op.tokentype}'", op)

    def parse_array(self):
        lbrace = self.cur()
        self.consume(TokenType.LBRACE)

        exprs = []
        errs = []
        while not self.eof():
            if self.match(TokenType.RBRACE):
                break
            try:
                if self.match(TokenType.LBRACE):
                    exprs.append(self.parse_array())
                elif self.match(TokenType.LCBRACE):
                    exprs.append(self.parse_table())
                else:
                    exprs.append(self.parse_expr())
                if not self.match(TokenType.COMMA):
                    break
                self.next()
            except ParseError as err:
                errs.append(err)
                self.sync()
            except ExceptionGroup as err:
                errs.extend(list(err.exceptions))
                self.sync()

        self.consume(TokenType.RBRACE)

        if len(errs):
            raise ExceptionGroup('one or more errors encountered while parsing array expression', errs)
        return expr.ArrayExpr(lbrace, exprs)

    def parse_table(self):
        lcbrace = self.cur()
        self.consume(TokenType.LCBRACE)
        statements = []
        errs = []

        while not self.match(TokenType.RCBRACE):
            if self.eof():
                errs.append(ParseError('unexpected eof encountered while parsing table expression', lcbrace))
                break

            try:
                statements.append(self.parse_statement())
                if not self.match(TokenType.COMMA):
                    break
                self.next()
            except ParseError as err:
                errs.append(err)
                self.sync()
            except ExceptionGroup as err:
                errs.extend(list(err.exceptions))
                self.sync()
        self.consume(TokenType.RCBRACE)

        if len(errs):
            raise ExceptionGroup('one or more errors encountered while parsing table expression', errs)
        return expr.TableExpr(lcbrace, statements)

    def parse_statement(self):
        errs = []

        identifier = self.cur()
        self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.EQUAL)

        expression = None
        if self.match(TokenType.LBRACE):
            expression = self.parse_array()
        elif self.match(TokenType.LCBRACE):
            expression = self.parse_table()
        else:
            expression = self.parse_expr()
        return expr.StatementExpr(identifier, expr.IdentifierExpr(identifier), expression)

    def parse(self, tokens):
        self.index = 0
        self.tokens = tokens

        statements = []
        errs = []
        while not self.eof():
            try:
                statements.append(self.parse_statement())
            except ParseError as err:
                errs.append(err)
                self.sync(identifier=True)
            except ExceptionGroup as err:
                errs.extend(list(err.exceptions))
                self.sync(identifier=True)
        if len(errs):
            raise ExceptionGroup('one or more errors encountered while parsing tokens', errs)
        return statements


def evaluate(statements):
    env = {}
    errs = []
    for statement in statements:
        try:
            statement.evaluate(env)
        except ExceptionGroup as err:
            errs.extend(list(err.exceptions))
        except expr.EvalError as err:
            errs.append(err)
    if len(errs):
        raise ExceptionGroup('one or more errors encountered while evaluating syntax tree', errs)
    return env

def loads(s):
    def report_errors(err):
        for e in err.exceptions:
            print(e.message)
            beg = linecolumn(s, e.token.beg)
            end = linecolumn(s, e.token.end)
            print(f"at line {beg[0]} columns {beg[1]} to {end[1]}")
            line = getline(s, beg)
            print(f"{line[0:beg[1]-1]}**{line[beg[1]-1:end[1]-1]}**{line[end[1]-1:-1]}")

    t = Tokenizer()
    tokens = t.tokenize(s)
    p = Parser()

    statements = None
    try:
        statements = p.parse(tokens)
        return evaluate(statements)
    except ExceptionGroup as err:
        report_errors(err)

def load(f):
    return loads(f.read())

def dump_item(item):
    match item:
        case bool():
            if item:
                return "true"
            else:
                return "false"
        case int() | float():
            return str(item)
        case str():
            return f"\"{item}\""
        case list():
            strs = []
            for x in item:
                strs.append(dump_item(x))
            return f"[{', '.join(strs)}]"
        case dict():
            statements = []
            for k, v in item.items():
                statement = f"{k} = {dump_item(v)}"
                statements.append(statement)
            return '{' + ', '.join(statements) + '}'
    return '0'

def dumps(d):
    statements = []
    for k, v in d.items():
        statement = f"{k} = {dump_item(v)}"
        statements.append(statement)
    return '\n'.join(statements)

def dump(d, f):
    data = dumps(d)
    f.write(data)

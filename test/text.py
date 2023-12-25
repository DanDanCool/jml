from pathlib import Path
import jml

path = Path('test.jml')

t = jml.Tokenizer()
tokens = t.tokenize(path.read_text())
#t.pretty_print(tokens)

p = jml.Parser()
statements = p.parse(tokens)
env = jml.evaluate(statements)
print(env)

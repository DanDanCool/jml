from pathlib import Path
import jml

path = Path('test.jml')

#t = jml.Tokenizer()
#tokens = t.tokenize(path.read_text())
##t.pretty_print(tokens)
#
#p = jml.Parser()
#statements = p.parse(tokens)
#env = jml.evaluate(statements)
#print(env)

with open('test.jml', 'r') as f:
    data = jml.load(f)
    print(data)

with open('dump.jml', 'w') as f:
    jml.dump(data, f)

with open('dump.jml', 'r') as f:
    data2 = jml.load(f)
    print(data2)


from pathlib import Path
import jmllib

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
    data = jmllib.load(f)
    print(data)

with open('dump.jml', 'w') as f:
    jmllib.dump(data, f)

with open('dump.jml', 'r') as f:
    data2 = jmllib.load(f)
    print(data2)


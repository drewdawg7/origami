from parser import *
prs = Parser()

val = prs.produce_ast(TEST_SQL)
print(val)
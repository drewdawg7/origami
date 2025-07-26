from parser import *


TEST_SQL="""
CREATE TABLE users (
  id INT NOT NULL,
  name VARCHAR(64),
);

ALTER TABLE users
ADD COLUMN email VARCHAR(64) NOT NULL,
ADD COLUMN age INT;
"""
print(f'Parsing: \n{TEST_SQL}\ninto\n')
prs = Parser()

val = prs.produce_ast(TEST_SQL)
print("Original AST:")
print(val)

# Add the folding functionality
folded_ast = val.fold_alter_statements()
print("\nFolded AST:")
print(folded_ast.body[0].sql())
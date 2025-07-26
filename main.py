from parser import Parser


TEST_SQL="""
CREATE TABLE users (
  id INT PRIMARY KEY NOT NULL,
  name VARCHAR(64),
);

CREATE TABLE position (
  id INT PRIMARY KEY NOT NULL,
  title VARCHAR(64)
)

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
print(folded_ast.sql())
from parser import Parser
from lexer import tokenize


TEST_SQL="""
CREATE TABLE users (
  id INT PRIMARY KEY NOT NULL,
  name VARCHAR(64),
  uselesscol INT
);

CREATE TABLE position (
  id INT PRIMARY KEY NOT NULL,
  title VARCHAR(64)
)

ALTER TABLE users
ADD COLUMN email VARCHAR(64) NOT NULL,
ADD COLUMN age INT,
DROP COLUMN uselesscol;
"""

TEST_SQL2="""
INSERT INTO users (id, name) VALUES
 (1, 'Drew'),
 (2, 'Ethan');
"""


def print_tokens():
  tokens = tokenize(TEST_SQL)
  print(tokens)


def print_ast():

  prs = Parser()

  val = prs.produce_ast(TEST_SQL)
  print(f'Parsing: \n{TEST_SQL}\n')
  print("===============================")
  print(val)

  folded_ast = val.fold_alter_statements()
  print("\nFolded SQL:")
  print(folded_ast.sql())

def print_sql():
  prs = Parser()
  val = prs.produce_ast(TEST_SQL)
  print("ORIGINAL SQL\n")
  print(TEST_SQL)
  print("\nPARSED AST TO SQL\n")
  print(val.sql())
  print("\nFOLDING ------->\n")
  print(val.fold().sql())

# print_tokens()
# print_ast()
print_sql()
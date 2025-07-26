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
INSERT INTO users (id, name)
VALUES (1, 'Drew');
"""


def print_tokens():
  tokens = tokenize(TEST_SQL2)
  print(tokens)


def print_ast():

  prs = Parser()

  val = prs.produce_ast(TEST_SQL2)
  print(f'Parsing: \n{TEST_SQL}\ninto\n')
  print("===============================")
  print(val)


  # Add the folding functionality
  # folded_ast = val.fold_alter_statements()
  # print("\nFolded SQL:")
  # print(folded_ast.sql())



print_tokens()
print_ast()
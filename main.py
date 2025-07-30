from parser import Parser
from lexer import tokenize


test_scripts_path = './test_scripts/'

table_operations = open(f'{test_scripts_path}table_operations.sql')
insert_statements = open(f'{test_scripts_path}insert_statements.sql')
create_table = open(f'{test_scripts_path}create_table.sql')

TEST_SQL = table_operations.read()
TEST_SQL2 = insert_statements.read()
TEST_SQL3 = """
UPDATE users
SET name = "Drew"
WHERE id=1;
"""
TEST_SQL4 = create_table.read()
TEST_SQL5="""
ALTER TABLE users
ADD COLUMN test INT NOT NULL PRIMARY KEY,
ADD COLUMN testTwo VARCHAR(64),
DROP COLUMN testThree;
"""


def print_tokens():
  tokens = tokenize(TEST_SQL3)
  print(tokens)


def print_ast():

  prs = Parser()

  val = prs.produce_ast(TEST_SQL3)
  print(f'Parsing: \n{TEST_SQL3}\n')
  print("===============================")
  print(val)

  # folded_ast = val.fold_alter_statements()
  # print("\nFolded SQL:")
  # print(folded_ast.sql())

def print_sql():
  prs = Parser()
  val = prs.produce_ast(TEST_SQL2)
  print("ORIGINAL SQL\n")
  print(TEST_SQL2)
  print("\nPARSED AST TO SQL\n")
  print(val.sql())
  # print("\nFOLDING ------->\n")
  # print(val.fold().sql())

# print_tokens()
# print_ast()
print_sql()
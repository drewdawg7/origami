from parser import Parser
from lexer import tokenize


test_scripts_path = './test_scripts/'

table_operations = open(f'{test_scripts_path}table_operations.sql')
insert_statements = open(f'{test_scripts_path}insert_statements.sql')

TEST_SQL = table_operations.read()
TEST_SQL2 = insert_statements.read()
TEST_SQL3 = """
UPDATE users
SET name = "Drew"
WHERE id=1;
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
  val = prs.produce_ast(TEST_SQL3)
  print("ORIGINAL SQL\n")
  print(TEST_SQL3)
  print("\nPARSED AST TO SQL\n")
  print(val.sql())
  # print("\nFOLDING ------->\n")
  # print(val.fold().sql())

# print_tokens()
# print_ast()
print_sql()
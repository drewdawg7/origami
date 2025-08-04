from parser import Parser
from lexer import tokenize


test_scripts_path = './test_scripts/'

table_operations = open(f'{test_scripts_path}table_operations.sql')
insert_statements = open(f'{test_scripts_path}insert_statements.sql')
create_table = open(f'{test_scripts_path}create_table.sql')
shop_tables = open(f'{test_scripts_path}shop_tables.sql')

TEST_SQL = shop_tables.read()
TEST_SQL2 = insert_statements.read()
TEST_SQL3 = """
CREATE TABLE users (
  id TINYINT(11) DEFAULT 1 UNIQUE,
  PRIMARY KEY (id),
  CONSTRAINT test FOREIGN KEY (name) REFERENCES otherTable(name)
);"""


def print_tokens():
  tokens = tokenize(TEST_SQL)
  print(tokens)


def print_ast():

  prs = Parser()

  val = prs.produce_ast(TEST_SQL)
  print(f'Parsing: \n{TEST_SQL}\n')
  print("===============================")
  print(val)

def print_sql():
  prs = Parser()
  val = prs.produce_ast(TEST_SQL)
  print("ORIGINAL SQL\n")
  print(TEST_SQL)
  print("\nPARSED AST TO SQL\n")
  print("\nFOLDING ------->\n")
  print(val.fold().sql())

# print_tokens()
# print_ast()
print_sql()
import sys
import os

# Get the absolute path to the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Insert at position 0 to take precedence over any other modules
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from parser import Parser



test_scripts_path = './test_scripts/'

# TODO Need to update the script to match the simple create table above
# table_operations = open(f'{test_scripts_path}table_operations.sql')
# sql1 = table_operations.read()

sql1 = """
CREATE TABLE users (
  id INT PRIMARY KEY NOT NULL,
  name VARCHAR(64),
);
"""

insert_statements = open(f'{test_scripts_path}insert_statements.sql')
sql2 = insert_statements.read()

def assert_column(column, expected_name, expected_datatype, expected_constraints):
    assert column.name == expected_name
    assert column.datatype == expected_datatype
    if expected_constraints:
        assert(len(column.constraints) == len(expected_constraints))
        for i, constraint in enumerate(expected_constraints):
            assert column.constraints[i] == constraint
    else:
        assert len(column.constraints) == 0


def test_basic_create_with_constraints():
    parser = Parser()
    ast = parser.produce_ast(sql1)

    # One Create Table statement
    assert len(ast.body) == 1
    # Table is called users
    assert ast.body[0].table.name == 'users' 
    # Table has 2 columns
    assert len(ast.body[0].columns) == 2
    assert_column(ast.body[0].columns[0], 'id', 'INT', ["PRIMARY KEY", "NOT NULL"])
   
    assert_column(ast.body[0].columns[1], 'name', 'VARCHAR(64)', [])




def test_insert_statements():
    parser = Parser()
    ast = parser.produce_ast(sql2)

    # 1 INSERT statement
    assert len(ast.body) == 1

    # 2 columns being inserted into
    assert len(ast.body[0].columns) == 2

    # First column is id and second is name
    assert ast.body[0].columns[0] == 'id'
    assert ast.body[0].columns[1] == 'name'

    # 2 rows being inserted
    assert len(ast.body[0].values) == 2

    # First row is (1, Drew)
    assert ast.body[0].values[0][0].value == "1"
    assert ast.body[0].values[0][1].value == f"'Drew'"
    
    # Second row is (2, Ethan)
    assert ast.body[0].values[1][0].value == "2"
    assert ast.body[0].values[1][1].value == f"'Ethan'"

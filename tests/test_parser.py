import sys
import os

# Get the absolute path to the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Insert at position 0 to take precedence over any other modules
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from parser import Parser
sql1 = """
CREATE TABLE users (
  id INT PRIMARY KEY NOT NULL,
  name VARCHAR(64),
);
"""


def test_basic_create_with_constraints():
    parser = Parser()
    ast = parser.produce_ast(sql1)

    # One Create Table statement
    assert len(ast.body) == 1
    # Table is called users
    assert ast.body[0].table.name == 'users' 
    # Table has 2 columns
    assert len(ast.body[0].columns) == 2
    # First column is called id
    assert ast.body[0].columns[0].name == 'id'
    # First column is an INT
    assert ast.body[0].columns[0].datatype == "INT"
    # First column has 2 constraints
    assert len(ast.body[0].columns[0].constraints) == 2
    # The first constraint is PRIMARY KEY and the second is NOT NULL
    assert ast.body[0].columns[0].constraints[0] == "PRIMARY KEY"
    assert ast.body[0].columns[0].constraints[1] == "NOT NULL"


    # Second column is called name
    assert ast.body[0].columns[1].name == 'name'
    # Seond column is a VARCHAR(64)
    assert ast.body[0].columns[1].datatype == "VARCHAR(64)"
    #Second column has no constraints
    assert len(ast.body[0].columns[1].constraints) == 0


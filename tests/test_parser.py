import sys
import os

# Get the absolute path to the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Insert at position 0 to take precedence over any other modules
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from parser import Parser
from abstract_syntax_tree import ColumnDef, CreateTable, Insert



test_scripts_path = './test_scripts/'

create_table = open(f'{test_scripts_path}create_table.sql')
sql1 = create_table.read()
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

def assert_column_full(column, expected_column):
    assert_column(
        column,
        expected_column.name,
        expected_column.datatype,
        expected_column.constraints
    )

def assert_insert(insert_statement: Insert , expected_columns:list[str], expected_values:list[list[str]]):
    
    assert len(insert_statement.columns) == len(expected_columns)
    assert insert_statement.columns == expected_columns
    
    for i, value_list in enumerate(insert_statement.values):
        assert len(value_list) == len(expected_columns)
        for j, value_literal in enumerate(value_list): 
            assert value_literal.value == expected_values[i][j]

def assert_create_table(create_table_statement: CreateTable, expected_table_name:str, expected_columns: list[ColumnDef] ):
    assert create_table_statement.table.name == expected_table_name
    for i, column in enumerate(create_table_statement.columns):
        assert_column_full(column, expected_columns[i])

    

def test_basic_create_with_constraints():
    parser = Parser()
    ast = parser.produce_ast(sql1)

    # One Create Table statement
    assert len(ast.body) == 1

    expected_column1 = ColumnDef(name='id', datatype='INT', constraints=["PRIMARY KEY", "NOT NULL"])
    expected_column2 = ColumnDef(name='name', datatype='VARCHAR(64)', constraints=[])
    assert_create_table(ast.body[0], 'users', [expected_column1, expected_column2])

def test_insert_statements():
    parser = Parser()
    ast = parser.produce_ast(sql2)
    assert len(ast.body) == 1
    assert_insert(
     insert_statement=ast.body[0],   
     expected_columns=['id', 'name'],
     expected_values=[
         ["1", "'Drew'"],
         ["2", "'Ethan'"]
     ]
    )
import sys
import os

# Get the absolute path to the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Insert at position 0 to take precedence over any other modules
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from parser import Parser
from abstract_syntax_tree import ColumnDef, CreateTable, Insert, AlterTable



test_scripts_path = './test_scripts/'

create_table = open(f'{test_scripts_path}create_table.sql')
sql1 = create_table.read()
insert_statements = open(f'{test_scripts_path}insert_statements.sql')
sql2 = insert_statements.read()
table_operations = open(f'{test_scripts_path}table_operations.sql')
sql3 = table_operations.read()

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


# ...existing code...

def assert_alter_table(alter_table_statement: AlterTable, expected_table_name: str, 
                      expected_add_columns: list[ColumnDef] = None, 
                      expected_drop_columns: list[str] = None):
    assert alter_table_statement.table.name == expected_table_name
    
    # Get add and drop operations from operations list
    add_operations = [op for op in alter_table_statement.operations if op.action == "ADD"]
    drop_operations = [op for op in alter_table_statement.operations if op.action == "DROP"]
    
    if expected_add_columns:
        assert len(add_operations) == len(expected_add_columns)
        for i, op in enumerate(add_operations):
            assert_column_full(op.column, expected_add_columns[i])
    
    if expected_drop_columns:
        assert len(drop_operations) == len(expected_drop_columns)
        for i, op in enumerate(drop_operations):
            assert op.column.name == expected_drop_columns[i]

def test_table_operations():
    parser = Parser()
    ast = parser.produce_ast(sql3)
    
    # Three statements: two CREATE TABLE and one ALTER TABLE
    assert len(ast.body) == 3
    
    # Test first CREATE TABLE (users)
    expected_users_columns = [
        ColumnDef(name='id', datatype='INT', constraints=["PRIMARY KEY", "NOT NULL"]),
        ColumnDef(name='name', datatype='VARCHAR(64)', constraints=[]),
        ColumnDef(name='uselesscol', datatype='INT', constraints=[])
    ]
    assert_create_table(ast.body[0], 'users', expected_users_columns)
    
    # Test second CREATE TABLE (position)
    expected_position_columns = [
        ColumnDef(name='id', datatype='INT', constraints=["PRIMARY KEY", "NOT NULL"]),
        ColumnDef(name='title', datatype='VARCHAR(64)', constraints=[])
    ]
    assert_create_table(ast.body[1], 'position', expected_position_columns)
    
    # Test ALTER TABLE statement
    expected_add_columns = [
        ColumnDef(name='email', datatype='VARCHAR(64)', constraints=["NOT NULL"]),
        ColumnDef(name='age', datatype='INT', constraints=[])
    ]
    expected_drop_columns = ['uselesscol']
    
    assert_alter_table(
        alter_table_statement=ast.body[2],
        expected_table_name='users',
        expected_add_columns=expected_add_columns,
        expected_drop_columns=expected_drop_columns
    )
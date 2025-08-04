import sys
import os

# Get the absolute path to the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if project_root not in sys.path:
    sys.path.insert(0, project_root)


from parser import Parser
from abstract_syntax_tree import ColumnDef, CreateTable, Insert, AlterTable, Update



test_scripts_path = './test_scripts/'

create_table = open(f'{test_scripts_path}create_table.sql')
sql1 = create_table.read()
insert_statements = open(f'{test_scripts_path}insert_statements.sql')
sql2 = insert_statements.read()
table_operations = open(f'{test_scripts_path}table_operations.sql')
sql3 = table_operations.read()
update_statements = open(f'{test_scripts_path}update_statements.sql')
sql4 = update_statements.read()
shop_tables = open(f'{test_scripts_path}shop_tables.sql')
sql5 = shop_tables.read()

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


def assert_alter_table(alter_table_statement: AlterTable, expected_table_name: str, 
                      expected_add_columns: list[ColumnDef] = None, 
                      expected_drop_columns: list[str] = None):
    assert alter_table_statement.table.name == expected_table_name
    
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

def assert_update(update_statement: Update, expected_table_name: str, 
                 expected_columns: list[str], expected_values: list[str],
                 expected_conditions: list[tuple[str, str, str]]):
    assert update_statement.table_name == expected_table_name
    
    # Check columns and values match
    assert len(update_statement.columns) == len(expected_columns)
    assert update_statement.columns == expected_columns
    
    for i, value_literal in enumerate(update_statement.values):
        assert value_literal.value == expected_values[i]
    
    # Check conditions
    assert len(update_statement.conditions) == len(expected_conditions)
    for i, condition in enumerate(update_statement.conditions):
        exp_col, exp_op, exp_val = expected_conditions[i]
        assert condition.column == exp_col
        assert condition.operator == exp_op
        assert condition.value.value == exp_val

# Add this test function
def test_update_statements():
    parser = Parser()
    ast = parser.produce_ast(sql4)
    assert len(ast.body) == 1
    assert_update(
        update_statement=ast.body[0],
        expected_table_name='users',
        expected_columns=['name'],
        expected_values=["'Drew'"],
        expected_conditions=[('id', '=', '1')]
    )


def test_shop_tables():
    parser = Parser()
    ast = parser.produce_ast(sql5).fold()
    
    assert len(ast.body) == 9
    
    expected_products_columns = [
        ColumnDef(name='id', datatype='INT', constraints=["PRIMARY KEY", "NOT NULL"]),
        ColumnDef(name='name', datatype='VARCHAR(100)', constraints=["NOT NULL"]),
        ColumnDef(name='price', datatype='DECIMAL(10,2)', constraints=[]),
        ColumnDef(name='category', datatype='VARCHAR(50)', constraints=[]),
        ColumnDef(name='created_at', datatype='TIMESTAMP', constraints=[]),
        ColumnDef(name='is_available', datatype='BOOLEAN', constraints=[]),
        ColumnDef(name='description', datatype='TEXT', constraints=[]),
        ColumnDef(name='weight', datatype='DECIMAL(6,2)', constraints=[])
    ]
    assert_create_table(ast.body[0], 'products', expected_products_columns)
    
    expected_orders_columns = [
        ColumnDef(name='order_id', datatype='INT', constraints=["PRIMARY KEY", "NOT NULL"]),
        ColumnDef(name='customer_id', datatype='INT', constraints=["NOT NULL"]),
        ColumnDef(name='total', datatype='DECIMAL(12,2)', constraints=[]),
        ColumnDef(name='created_at', datatype='TIMESTAMP', constraints=["NOT NULL"])
    ]
    assert_create_table(ast.body[1], 'orders', expected_orders_columns)
    
    expected_order_items_columns = [
        ColumnDef(name='item_id', datatype='INT', constraints=["PRIMARY KEY", "NOT NULL"]),
        ColumnDef(name='order_id', datatype='INT', constraints=["NOT NULL"]),
        ColumnDef(name='product_id', datatype='INT', constraints=["NOT NULL"]),
        ColumnDef(name='quantity', datatype='INT', constraints=[])
    ]
    assert_create_table(ast.body[2], 'order_items', expected_order_items_columns)
    
    assert_insert(
        insert_statement=ast.body[3],
        expected_columns=['id', 'name', 'price', 'category'],
        expected_values=[
            ["1", "'Laptop'", "999.99", "'Electronics'"],
            ["2", "'Desk Chair'", "249.50", "'Furniture'"],
            ["3", "'Coffee Mug'", "12.99", "'Kitchenware'"]
        ]
    )
    
    assert_insert(
        insert_statement=ast.body[4],
        expected_columns=['order_id', 'customer_id', 'total'],
        expected_values=[["101", "5", "1249.48"]]
    )
    
    assert_insert(
        insert_statement=ast.body[5],
        expected_columns=['item_id', 'order_id', 'product_id', 'quantity'],
        expected_values=[
            ["1001", "101", "1", "1"],
            ["1002", "101", "3", "2"]
        ]
    )
    
    assert_update(
        update_statement=ast.body[6],
        expected_table_name='products',
        expected_columns=['price'],
        expected_values=["1099.99"],
        expected_conditions=[('id', '=', '1')]
    )
    
    assert_update(
        update_statement=ast.body[7],
        expected_table_name='order_items',
        expected_columns=['quantity'],
        expected_values=["3"],
        expected_conditions=[('order_id', '=', '101'), ('product_id', '=', '3')]
    )
    
    assert_update(
        update_statement=ast.body[8],
        expected_table_name='products',
        expected_columns=['is_available'],
        expected_values=["false"],
        expected_conditions=[('category', '=', "'Electronics'")]
    )
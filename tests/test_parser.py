import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parser import Parser

def setup_parser(sql: str):
    parser = Parser(dialect="mysql")
    parser.combined_sql = sql;
    
    return parser


sql = """
    CREATE TABLE users (id INT, name varchar(64));
    """

sql2 ="""
CREATE TABLE users (id INT, name varchar(64));
ALTER TABLE users
ADD COLUMN email varchar(64);
""" 

sql3 ="""
CREATE TABLE users (id INT, name varchar(64));
ALTER TABLE users
DROP COLUMN name;
""" 
sql4 ="""
CREATE TABLE users (id INT, name varchar(64));
ALTER TABLE users
DROP COLUMN name;
ALTER TABLE users
ADD COLUMN email varchar(64);
""" 

sql5 ="""
CREATE TABLE users(
    id INT NOT NULL,
    name VARCHAR(64),
    PRIMARY KEY (id)
);
"""


def test_create_table_statement():
    parser = setup_parser(sql)
    parser.parse_sql()
    assert len(parser.tables) == 1
    assert len(parser.tables[0].columns) == 2
    assert parser.tables[0].name == "users"
    assert parser.tables[0].columns[0].name == "id"
    assert parser.tables[0].columns[1].name == "name"
    assert parser.tables[0].columns[0].datatype == "INT"
    assert parser.tables[0].columns[1].datatype == "VARCHAR"

    
def test_create_and_alter_table():
    parser = setup_parser(sql2)
    parser.parse_sql()
    parser.merge()
    assert len(parser.tables[0].columns) == 3
    assert parser.tables[0].columns[2].name == "email"
    assert parser.tables[0].columns[2].datatype == "VARCHAR"

def test_create_and_alter_table_drop_col():
    parser = setup_parser(sql3)
    parser.parse_sql()
    parser.merge()
    assert len(parser.tables[0].columns) == 1
    assert parser.tables[0].columns[0].name == "id"
    assert parser.tables[0].columns[0].datatype == "INT"

def test_create_and_alter_table_add_and_drop_col():
    parser = setup_parser(sql4)
    parser.parse_sql()
    parser.merge()
    assert len(parser.tables[0].columns) == 2
    assert parser.tables[0].columns[1].name == "email"
    assert parser.tables[0].columns[1].datatype == "VARCHAR"   


def test_constraints():
    parser = setup_parser(sql5)
    parser.parse_sql()
    parser.merge()
    assert len(parser.tables[0].columns[0].constraints) == 2




parser = setup_parser(sql5);
parser.parse_sql();
parser.merge();
for table in parser.tables:
    print(table)

# parser.parse_sql_into_statements()
# print(parser.tables[0])
# stmt = parser.stmts[0]
# print(f'arg types: {stmt.arg_types}')
# print(f'args: {stmt.args}')
# print(f'exprs: {stmt.this.expressions[2]}')
# print(f'expr key: {stmt.this.expressions[2].key}')
# print(f'col name: {stmt.this.expressions[2].args.get("expressions")[0].args.get("this")}')
# print(f'key: {stmt.key}')
# print(f'kind: {stmt.args.get("kind")}')
# # print(f'name: {stmt.this.this.name}')
# print(f'action key: {stmt.args.get("actions")[0].key}')
# # print(f'action keys: {stmt.args.get("actions")[0].args.keys()}')

# # print(f'action type: {stmt.args.get("actions")[0].args.get("kind").this.name}')
# # print(f'action name: {stmt.args.get("actions")[0].this.name}')
# # print("args keys:", stmt.args.keys())
# # # print("full args:", stmt.args)
# # for expr in stmt.this.expressions:
# #     print(expr.args.keys())
# #     print(expr.this.name)
# #     print(expr.kind.this.name)
# # print(f'columns: {stmt.this.this.expression}')
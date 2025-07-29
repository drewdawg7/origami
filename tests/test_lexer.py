import sys
import os

# Get the absolute path to the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Insert at position 0 to take precedence over any other modules
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from lexer import TokenType, Token, tokenize

test_scripts_path = './test_scripts/'

create_table = open(f'{test_scripts_path}create_table.sql')
sql1 = create_table.read()
insert_statements = open(f'{test_scripts_path}insert_statements.sql')
sql2 = insert_statements.read()

def assert_tokens(tokens: list[Token], expected_tokens: list[Token]):
    assert len(tokens) == len(expected_tokens)

    for i, token in enumerate(tokens):
        assert token.type == expected_tokens[i].type
        assert token.value == expected_tokens[i].value

def test_create_table():
    tokens = tokenize(sql1)

    expected_tokens = [
        Token(type=TokenType.KEYWORD, value="CREATE"),
        Token(type=TokenType.KEYWORD, value="TABLE"),
        Token(type=TokenType.IDENTIFIER, value="users"),
        Token(type=TokenType.LEFT_PAREN, value="("),
        Token(type=TokenType.IDENTIFIER, value="id"),
        Token(type=TokenType.DATATYPE, value="INT"),
        Token(type=TokenType.KEYWORD, value="PRIMARY"),
        Token(type=TokenType.KEYWORD, value="KEY"),
        Token(type=TokenType.KEYWORD, value="NOT"),
        Token(type=TokenType.KEYWORD, value="NULL"),
        Token(type=TokenType.DELIMITER, value=","),
        Token(type=TokenType.IDENTIFIER, value="name"),
        Token(type=TokenType.DATATYPE, value="VARCHAR"),
        Token(type=TokenType.LEFT_PAREN, value="("),
        Token(type=TokenType.LITERAL, value="64"),
        Token(type=TokenType.RIGHT_PAREN, value=")"),
        Token(type=TokenType.DELIMITER, value=","),
        Token(type=TokenType.RIGHT_PAREN, value=")"),
        Token(type=TokenType.DELIMITER, value=";"),
        Token(type=TokenType.EOF, value="End of File"),
    ]

    assert_tokens(tokens, expected_tokens)

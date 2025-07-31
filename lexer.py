from enum import Enum
from pydantic.dataclasses import dataclass




KEYWORDS = [
    'CREATE',
    'TABLE',
    'ALTER',
    'ADD',
    'DROP',
    'COLUMN',
    'INSERT',
    'INTO',
    'UPDATE',
    'WHERE',
    'SET',
    'PRIMARY',
    'KEY',
    'LITERAL',
    'NOT',
    'NULL',
    'VALUES',
    'UNIQUE',
    'IF',
    'EXISTS',
    'AUTO_INCREMENT',
    'CONSTRAINT',
    'FOREIGN',
    'REFERENCES',
    'DEFAULT'
]

DATATYPE = [
    'INT',
    'VARCHAR',
    'TINYINT',
]

TokenType = Enum(
    'TokenType',
    [
        'KEYWORD',
        'IDENTIFIER',
        'DATATYPE',
        'LEFT_PAREN',
        'RIGHT_PAREN',
        'LITERAL',
        'DELIMITER',
        'EOF',
        'EQUALS',
        'UKNOWN'
    ]
)


@dataclass
class Token:
    value: str
    type:  TokenType

    def __str__(self) -> str:
        return f"\nvalue: \"{self.value}\" type: {self.type.name}"
    
    def __repr__(self) -> str:
        return self.__str__()

def isalpha(src:str) -> bool:
    return src.isalpha()

def isint(src:str) -> bool:
    return src.isdigit()

def isskippable(src:str) -> bool:
    return src == ' ' or src == '\n' or src == '\t'

def create_token_from_string(string: str)->Token:
    if (string in KEYWORDS):
        return Token(value=string, type=TokenType.KEYWORD)
    elif (string in DATATYPE):
        return Token(value=string, type=TokenType.DATATYPE)
    else:
        return Token(value=string, type=TokenType.IDENTIFIER)

def tokenize(sourceCode: str) -> list[Token]:
    tokens:list[Token] = []
    src = list(sourceCode)
    
    while (len(src) > 0):
        token = None
        if (isskippable(src[0])):
            src.pop(0)
            continue
        elif (src[0] == '('):
            token = Token(value=src.pop(0), type=TokenType.LEFT_PAREN)
        elif (src[0] == ')'):
            token = Token(value=src.pop(0), type=TokenType.RIGHT_PAREN)
        elif (src[0] == ','):
            token = Token(value=src.pop(0), type=TokenType.DELIMITER)
        elif (src[0] == ';'):
            token = Token(value=src.pop(0), type=TokenType.DELIMITER)
        elif (src[0] == '='):
            token = Token(value=src.pop(0), type=TokenType.EQUALS)
        else:
            if (src[0] == "'" or src[0] == '"'):
                quote_char = src.pop(0)
                string_value = f"{quote_char}"
                while (len(src) > 0 and src[0] != quote_char):
                    string_value += src.pop(0)

                if len(src) > 0 and src[0] == quote_char:
                    string_value += src.pop(0)
                    token = Token(value=string_value, type=TokenType.LITERAL)
                else:
                    raise Exception("Expected closing quote")
            else: 
                if (isint(src[0])):
                    num = ""
                    while (len(src) > 0 and isint(src[0])):
                        num += src.pop(0)
                    token = Token(value=num, type=TokenType.LITERAL)
                    num = ""
                elif (isalpha(src[0]) or src[0] == '_'):
                    string = ""
                    while (len(src) > 0 and (isalpha(src[0]) or src[0] == '_') and src[0] != " "):
                        string += src.pop(0)
                        token = create_token_from_string(string)
                else:
                    raise Exception("Unexpected non-digit, non-alpha char encountered")

        if (token is None):
            token = Token(value=src.pop(0), type=TokenType.UKNOWN)
        # print(f'Token: {token}')
        tokens.append(token)
    tokens.append(Token(value='End of File', type=TokenType.EOF))
    return tokens




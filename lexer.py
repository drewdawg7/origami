from enum import Enum, IntEnum
from pydantic.dataclasses import dataclass




KEYWORDS = [
    'CREATE',
    'TABLE',
    'ALTER',
    'DROP',
    'COLUMN',
    'ADD',
    'INSERT',
    'UPDATE',
    'PRIMARY',
    'KEY',
    'LITERAL',
    'NOT',
    'NULL'
]

DATATYPE = [
    'INT',
    'VARCHAR'
]

TokenType = Enum(
    'TokenType',
    [
        'KEYWORD',
        'IDENTIFIER',
        'DATATYPE',
        'LEFT_PAREN',
        'RIGHT_PAREN',
        'INTEGER',
        'DELIMITER',
        'EOF',
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
        else: 
            if(isint(src[0])):
                num = ""
                while (len(src)> 0 and isint(src[0])):
                    num += src.pop(0)                
                token = Token(value=num, type=TokenType.INTEGER)
                num = ""
            elif (isalpha(src[0])):
                string = ""
                while (len(src) > 0 and isalpha(src[0]) and src[0] != " "):
                    string += src.pop(0)
                token = create_token_from_string(string)

        if (token == None):
            token = Token(value=src.pop(0), type=TokenType.UKNOWN)
        print(f'Token: {token}')
        tokens.append(token)
    tokens.append(Token(value='End of File', type=TokenType.EOF))
    return tokens




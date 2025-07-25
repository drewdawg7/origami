from abstract_syntax_tree import * 
from lexer import *






class Parser:
    tokens: list[Token] = []


    def produce_ast(self, sourceCode: str) -> Schema:
        schema:Schema = Schema()
        self.tokens = tokenize(sourceCode)

        while (self.not_eof()): 
            schema.body.append(self.parse_node())

        return schema

    def not_eof(self) -> bool:
        return self.tokens[0].type != TokenType.EOF
    
    def parse_node(self) -> Node:
        if self.tokens[0].type == TokenType.KEYWORD and self.tokens[0].value == 'CREATE':
            return self.parse_create_statement()
        self.tokens.pop(0)
        return None
    
    def parse_create_statement(self) -> Node:
        # If we're here we already know this is a CREATE token
        self.tokens.pop(0)

        if self.tokens[0].type != TokenType.KEYWORD or self.tokens[0].value != 'TABLE':
            raise Exception("Expected TABLE keyword after CREATE")
        self.tokens.pop(0)

        if self.tokens[0].type != TokenType.IDENTIFIER:
            raise Exception("Expected table name")
        
        table_name = self.tokens[0].value
        self.tokens.pop(0)
        table = Table(name=table_name)

        create_stmt = CreateTable(table=table)

        if self.tokens[0].type != TokenType.LEFT_PAREN:
            raise Exception("Expected opening parenthesis after table name")
        self.tokens.pop(0)

        while (self.not_eof() and self.tokens[0].type != TokenType.RIGHT_PAREN):
            column = self.parse_column_def()
            create_stmt.columns.append(column)
            if self.tokens[0].type == TokenType.DELIMITER and self.tokens[0].value == ',':
                self.tokens.pop(0)

        if self.tokens[0].type != TokenType.RIGHT_PAREN:
            raise Exception("Expected closing parenthesis")
        
        self.tokens.pop(0)
        if self.tokens[0].type == TokenType.DELIMITER and self.tokens[0].value == ';':
            self.tokens.pop(0)
        return create_stmt
    
    def parse_column_def(self) -> ColumnDef:
        column = ColumnDef()

        if self.tokens[0].type != TokenType.IDENTIFIER:
            raise Exception("Expected column name")
        column.name = self.tokens[0].value
        self.tokens.pop(0)

        if self.tokens[0].type != TokenType.DATATYPE:
            print(self.tokens[0].value)
            raise Exception("Expected datatype")
        column.datatype = self.tokens[0].value
        self.tokens.pop(0)

        if column.datatype == "VARCHAR" and self.tokens[0].type == TokenType.LEFT_PAREN:
            self.tokens.pop(0)
            if self.tokens[0].type != TokenType.INTEGER:
                raise Exception("Expected integer for VARCHAR length")
            column.datatype += f'({self.tokens[0].value})'
            self.tokens.pop(0)
            if self.tokens[0].type != TokenType.RIGHT_PAREN:
                raise Exception("Expected closing parenthesis after VARCHAR length")
            self.tokens.pop(0)

        
        return column


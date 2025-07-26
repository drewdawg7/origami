from abstract_syntax_tree import * 
from lexer import *






class Parser:
    tokens: list[Token] = []


    def produce_ast(self, sourceCode: str) -> Schema:
        schema:Schema = Schema()
        self.tokens = tokenize(sourceCode)

        while (self.not_eof()): 
            node = self.parse_node()
            if node != None:
                schema.body.append(node)

        return schema

    def not_eof(self) -> bool:
        return self.tokens[0].type != TokenType.EOF
    
    def parse_node(self) -> Node:
        if self.is_keyword():
            if self.curr_value() == 'CREATE':
                return self.parse_create_statement()
            elif self.curr_value() == 'ALTER':
                return self.parse_alter_statement()
            elif self.curr_value() == 'INSERT':
                return self.parse_insert_statement()
         
        
        self.next()
        return None
    
    def parse_insert_statement(self) -> Node:
        columns = []
        values = []
        self.next()
        if not self.is_keyword() and self.curr_value() != 'INTO':
            raise Exception("Expected INTO after INSERT")
        self.next()
        if not self.is_identifier():
            raise Exception("Expected table name after INSERT INTO")
        table_name = self.curr_value()
        self.next()
        if not self.is_left_paren():
            raise Exception("Expected opening parenthesis after table name")
        self.next()
        while self.curr_type() == TokenType.IDENTIFIER or self.is_comma():
            print(f'Token in Column Loop: {self.curr_token()}')
            if self.is_comma():
                self.next()
            elif self.curr_type() == TokenType.IDENTIFIER:
                columns.append(self.curr_value())
                self.next()
            else:
                raise Exception(f'Found unexpected token while parsing INSERT statemnt: {self.curr_token()}') 
        if (not self.is_right_paren()):
            raise Exception(f'Expected closing parenthesis after columns in INSERT: {self.curr_token()}')
        self.next()
        if (self.curr_type() != TokenType.KEYWORD and self.curr_value() != 'VALUES'):
            raise Exception(f'Expected VALUES after columns while parsing INSERT: {self.curr_token()}')
        self.next()
        if (not self.is_left_paren()):
            raise Exception(f'Expected opening parenthesis after VALUES')
        self.next()
        # print(f'Token before Value Loop: {self.curr_token()}')
        while self.curr_type() == TokenType.LITERAL or self.is_comma():
            # print(f'Token in Value Loop: {self.curr_token()}')
            if self.is_comma():
                self.next()
            elif self.curr_type() == TokenType.LITERAL:
                values.append(self.curr_value())
                self.next()
            else:
                raise Exception(f'Found unexpected token while parsing INSERT statement: {self.curr_token()}')
            
        if (not self.is_right_paren()):
            raise Exception(f'Expected closing parenthesis after values in INSERT: {self.curr_token()}')
        self.next()
        if (not self.is_semicolon()):
            raise Exception(f'Expected semicolon after closing parenthesis')
        
        if (len(columns) != len(values)):
            raise Exception(f'Columns and values have a mismatched length')
        value_literals = []
        for val in values:
            value_literals.append(ValueLiteral(value=val))
        insert_stmt = Insert(table_name=table_name, columns=columns, values=[value_literals])
        return insert_stmt
                 
        
        

    def parse_create_statement(self) -> Node:
        # If we're here we already know this is a CREATE token
        self.next()

        if not self.is_keyword() and self.curr_value() != 'TABLE':
            raise Exception("Expected TABLE keyword after CREATE")
        self.next()

        if not self.is_identifier():
            raise Exception("Expected table name")
        
        table_name = self.curr_value()
        self.next()
        table = Table(name=table_name)

        create_stmt = CreateTable(table=table)

        if not self.is_left_paren():
            raise Exception("Expected opening parenthesis after table name")
        self.next()

        while (self.not_eof() and not self.is_right_paren()):
            column = self.parse_column_def()
            create_stmt.columns.append(column)
            if self.is_comma():
                self.next()

        if not self.is_right_paren():
            raise Exception("Expected closing parenthesis")
        
        self.next()
        if self.is_semicolon():
            self.next()
        return create_stmt
    
    def parse_column_def(self) -> ColumnDef:
        column = ColumnDef()

        if self.curr_type() != TokenType.IDENTIFIER:
            raise Exception("Expected column name")
        column.name = self.tokens[0].value
        self.next()

        if self.curr_type() != TokenType.DATATYPE:
            raise Exception("Expected datatype")
        column.datatype = self.curr_value()
        self.next()

        if column.datatype == "VARCHAR" and self.is_left_paren():
            self.next()
            if self.curr_type() != TokenType.INTEGER:
                raise Exception("Expected integer for VARCHAR length")
            column.datatype += f'({self.tokens[0].value})'
            self.next()
            if not self.is_right_paren():
                raise Exception("Expected closing parenthesis after VARCHAR length")
            self.next()

        while (self.not_eof() and not self.is_delimiter() and not self.is_right_paren()):
            if self.is_keyword() and self.tokens[0].value == "NOT":
                self.next()
                if self.is_keyword() and self.curr_value() == "NULL":
                    column.constraints.append("NOT NULL")
                    self.next()
                else:
                    raise Exception("Expected NULL after NOT")
            if self.is_keyword() and self.curr_value() == "PRIMARY":
                self.next()
                if self.is_keyword() and self.curr_value() == "KEY":
                    column.constraints.append("PRIMARY KEY")
                    self.next()
                else:
                    raise Exception("Expected KEY after Primary")

        return column
    
    def parse_alter_statement(self) -> Node:
        # Current node is ALTER so pop
        self.next()

        if not self.is_keyword() or self.curr_value() != 'TABLE':
            raise Exception("Expected TABLE keyword after ALTER")
        self.next()  # Skip TABLE

        if not self.is_identifier():
            raise Exception("Expected table name")
        table_name = self.curr_value()
        self.next()  # Skip table name
        table = Table(name=table_name)
        alter_stmt = AlterTable(table=table)
        alter_stmt.operations = []

        while self.not_eof() and not self.is_semicolon():
            if self.is_keyword():
                if self.curr_value() == 'ADD':
                    self.next()
                    if self.is_keyword() and self.curr_value() == 'COLUMN':
                        self.next()
                    column = self.parse_column_def()
                    operation = AlterOperation(action="ADD", column=column)
                    alter_stmt.operations.append(operation)

                elif self.curr_value() == 'DROP':
                    self.next()
                    if self.is_keyword() and self.curr_value() == 'COLUMN':
                        self.next()
                    if not self.is_identifier():
                        raise Exception("Expected column name after DROP COLUMN")
                    column_name = self.curr_value()
                    column = ColumnDef(name=column_name)
                    operation = AlterOperation(action="DROP", column=column)
                    alter_stmt.operations.append(operation)
                    self.next()
                else:
                    self.next()
            if self.is_comma():
                self.next()
            elif not self.is_semicolon():
                print(self.curr_type())
                raise Exception("Expected comma or semicolon after alter operation")
            
        if self.is_semicolon():
            self.next()

        return alter_stmt




    def is_keyword(self) -> bool:
        return self.curr_type() == TokenType.KEYWORD
    
    def is_identifier(self) -> bool:
        return self.curr_type() == TokenType.IDENTIFIER
    
    def is_semicolon(self) -> bool:
        return self.curr_type() == TokenType.DELIMITER and self.curr_value() == ';'
    
    def is_delimiter(self) -> bool:
        return self.curr_type() == TokenType.DELIMITER
    
    def is_comma(self) -> bool:
        return self.curr_type() == TokenType.DELIMITER and self.curr_value() == ','
    
    def is_left_paren(self) -> bool: 
        return self.tokens[0].type == TokenType.LEFT_PAREN
    
    def is_right_paren(self) -> bool:
        return self.tokens[0].type == TokenType.RIGHT_PAREN
    
    def curr_value(self) -> str:
        return self.tokens[0].value
    
    def curr_type(self) -> TokenType:
        return self.tokens[0].type
        
    def curr_token(self) -> Token:
        return self.tokens[0]

    def next(self) -> Token:
        return self.tokens.pop(0)


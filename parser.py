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
            elif self.curr_value() == 'UPDATE':
                return self.parse_update_statement()
         
        
        self.next()
        return None
    
    def parse_update_statement(self) -> Node:
        self.next()
   
        table_name = self.expect_identifier("table name")

        self.expect_keyword("SET")

        update_column_name = self.expect_identifier("column name")
        
        self.expect_token_type(TokenType.EQUALS, "after column name")
   
        if not self.is_literal():
            raise Exception(f"Expected literal after = : {self.curr_token()}")
        value = ValueLiteral(value = self.next().value)

        self.expect_keyword("WHERE")

        condition_column_name = self.expect_identifier("column name")
        if not self.is_equals():
            raise Exception(f"Expected condition operator in WHERE clause: {self.curr_token()}")
        condition_operator = self.next().value
        if not self.is_literal():
            raise Exception(f"Expected literal while parsing WHERE clause: {self.curr_token()}")
        condition_value = self.next().value
        if not self.is_semicolon():
            raise Exception(f"Expected semicolon while parsing WHERE clause: {self.curr_token()}")
        self.next()
        update_condition = UpdateCondition(column=condition_column_name, operator=condition_operator, value=ValueLiteral(value=condition_value))

        update_stmt = Update(table_name=table_name, columns=[update_column_name], values=[value], conditions=[update_condition])

        return update_stmt

    def parse_insert_statement(self) -> Node:
        columns = []
        
        self.next()

        self.expect_keyword("INTO")
        
        table_name = self.expect_identifier("table name")

        # if not self.is_left_paren():
        #     raise Exception("Expected opening parenthesis after table name")
        # self.next()
        self.expect_token_type(TokenType.LEFT_PAREN, "after table name")
        while self.curr_type() == TokenType.IDENTIFIER or self.is_comma():
            # print(f'Token in Column Loop: {self.curr_token()}')
            if self.is_comma():
                self.next()
            elif self.curr_type() == TokenType.IDENTIFIER:
                columns.append(self.curr_value())
                self.next()
            else:
                raise Exception(f'Found unexpected token while parsing INSERT statemnt: {self.curr_token()}') 

        self.expect_token_type(TokenType.RIGHT_PAREN, "after columns in INSERT")
        self.expect_keyword("VALUES")
      
        # print(f'Token before Value Loop: {self.curr_token()}')
        in_values = True
        all_values = []
        while (in_values):
            values = []
    
            self.expect_token_type(TokenType.LEFT_PAREN, "after VALUES")
            while self.curr_type() == TokenType.LITERAL or self.is_comma():
                # print(f'Token in Value Loop: {self.curr_token()}')
                if self.is_comma():
                    self.next()
                elif self.curr_type() == TokenType.LITERAL:
                    values.append(self.curr_value())
                    self.next()
                else:
                    raise Exception(f'Found unexpected token while parsing INSERT statement: {self.curr_token()}')
            
            
            self.expect_token_type(TokenType.RIGHT_PAREN, "after values in INSERT")
            
            if (not self.is_delimiter()):
                raise Exception(f'Expected semicolon or comma after closing parenthesis: {self.curr_token()}')
            if (self.is_semicolon()):
                in_values = False
            all_values.append(values)
            self.next()
            
        
        for val_list in all_values:
            if (len(columns) != len(val_list)):
                raise Exception(f'Columns and values have a mismatched length')
        value_literals = []
        for val_list in all_values:
            inner_value_literals = []
            for val in val_list: 
                inner_value_literals.append(ValueLiteral(value=val))
            value_literals.append(inner_value_literals)
        insert_stmt = Insert(table_name=table_name, columns=columns, values=value_literals)
        return insert_stmt
                 
        
        

    def parse_create_statement(self) -> Node:
        # If we're here we already know this is a CREATE token
        self.next()

        self.expect_keyword("TABLE")


        table_name = self.expect_identifier("table name")
        table = Table(name=table_name)

        create_stmt = CreateTable(table=table)

 

        self.expect_token_type(TokenType.LEFT_PAREN, "after table name")

        while (self.not_eof() and not self.is_right_paren()):
            column = self.parse_column_def()
            create_stmt.columns.append(column)
            if self.is_comma():
                self.next()

        self.expect_token_type(TokenType.RIGHT_PAREN)
        if self.is_semicolon():
            self.next()
        return create_stmt
    
    def parse_column_def(self) -> ColumnDef:
        column = ColumnDef()


        column.name = self.expect_identifier("column name")

        if self.curr_type() != TokenType.DATATYPE:
            raise Exception("Expected datatype")
        column.datatype = self.curr_value()
        self.next()

        if column.datatype == "VARCHAR" and self.is_left_paren():
            self.next()
            if self.curr_type() != TokenType.LITERAL:
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
                    raise Exception(f"Expected NULL after NOT: {self.curr_token()}")
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

        self.expect_keyword("TABLE")

        table_name = self.expect_identifier("table name")
        table = Table(name=table_name)
        alter_stmt = AlterTable(table=table)
        alter_stmt.operations = []

        while self.not_eof() and not self.is_semicolon():
            if self.is_keyword():
                if self.curr_value() == 'ADD':
                    self.next()
                    self.expect_keyword("COLUMN")
                    column = self.parse_column_def()
                    operation = AlterOperation(action="ADD", column=column)
                    alter_stmt.operations.append(operation)

                elif self.curr_value() == 'DROP':
                    self.next()
                    self.expect_keyword("COLUMN")
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
                raise Exception("Expected comma or semicolon after alter operation")
            
        if self.is_semicolon():
            self.next()

        return alter_stmt




    def expect_keyword(self, keyword:str ) -> None:
        if not self.is_keyword() or self.curr_value() != keyword:
            raise Exception(f"Expected {keyword} keyword, got: {self.curr_token()}")
        self.next()
        
    def expect_identifier(self, context: str = "") -> str:
        if not self.is_identifier():
            raise Exception(f"Expected identifier{' ' + context if context else ''}, got: {self.curr_token()}")
        return self.next().value
    
    def expect_token_type(self,  token_type: TokenType, context: str = "") -> Token:
        if self.curr_type() != token_type:
            raise Exception(f"Expected {token_type.name}{' ' + context if context else ''}, got: {self.curr_token()}")
        return self.next()

    
    def is_keyword(self) -> bool:
        return self.curr_type() == TokenType.KEYWORD
    
    def is_where(self) -> bool:
        return self.curr_type() == TokenType.KEYWORD and self.curr_value() == "WHERE"
    
    def is_literal(self) -> bool:
        return self.curr_type() == TokenType.LITERAL
    
    def is_equals(self) -> bool:
        return self.curr_type() == TokenType.EQUALS

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


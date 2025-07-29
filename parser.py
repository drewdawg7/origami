from abstract_syntax_tree import Node, Schema, ColumnDef, AlterOperation, AlterTable, Table, Insert, ValueLiteral, UpdateCondition, Update, CreateTable
from lexer import TokenType, Token, tokenize

class Parser:
    tokens: list[Token] = []


    def produce_ast(self, sourceCode: str) -> Schema:
        schema:Schema = Schema()
        self.tokens = tokenize(sourceCode)

        while (self.not_eof()): 
            node = self.parse_node()
            if node is not None:
                schema.body.append(node)

        return schema

    def not_eof(self) -> bool:
        return self.curr_type() != TokenType.EOF
    
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
   
        table_name = self.consume_identifier("table name")

        self.consume_keyword("SET")

        update_column_name = self.consume_identifier("column name")
        
        self.consume_token_type(TokenType.EQUALS, "after column name")
   

        value = ValueLiteral(value=self.consume_literal("after ="))

        self.consume_keyword("WHERE")

        condition_column_name = self.consume_identifier("column name")
        if not self.is_equals():
            raise Exception(f"Expected condition operator in WHERE clause: {self.curr_token()}")
        condition_operator = self.next().value

        condition_value = self.consume_literal("while parsing WHERE clause")
        self.consume_delimiter(";")
        update_condition = UpdateCondition(column=condition_column_name, operator=condition_operator, value=ValueLiteral(value=condition_value))

        update_stmt = Update(table_name=table_name, columns=[update_column_name], values=[value], conditions=[update_condition])

        return update_stmt

    
    
    def parse_insert_statement(self) -> Node:
        insert_parser = self.sequence(
            self.keyword("INSERT"),
            self.keyword("INTO"),
            self.identifier(),
            self.parse_column_list(),
            self.keyword("VALUES"),
            self.parse_value_lists()
        )
        results = insert_parser()
        if not results:
            return None
        _, _, table_name, columns, _, all_values = results
        for values in all_values:
            if len(columns) != len(values):
                raise Exception("Columns and values have mismatched lengths")
            
        value_literals = []
        for val_list in all_values:
            inner_value_literals = []
            for val in val_list:
                inner_value_literals.append(ValueLiteral(value=val))
            value_literals.append(inner_value_literals)
        return Insert(table_name=table_name, columns=columns, values=value_literals)

    def keyword(self, expected_word):
        def parser():
            saved_tokens = self.tokens.copy()
            if self.is_keyword() and self.curr_value() == expected_word:
                result = self.curr_value()
                self.next()
                return result
            self.tokens = saved_tokens
            return None
        return parser

    def identifier(self):
        def parser():
            saved_tokens = self.tokens.copy()
            if self.is_identifier():
                result = self.curr_value()
                self.next()
                return result
            self.tokens = saved_tokens
            return None
        return parser
    
    def literal(self):
        def parser():
            saved_tokens = self.tokens.copy()
            if self.is_literal():
                result = self.curr_value()
                self.next()
                return result
            self.tokens = saved_tokens
            return None
        return parser
    
    def token_type(self, expected_type):
        def parser():
            saved_tokens = self.tokens.copy()
            if self.curr_type() == expected_type:
                result = self.curr_token()
                self.next()
                return result
            self.tokens = saved_tokens
            return None
        return parser
    
    def delimiter(self, expected_delimiter):
        def parser():
            saved_tokens = self.tokens.copy()
            if self.is_delimiter() and self.curr_value() == expected_delimiter:
                result = self.curr_token()
                self.next()
                return result
            self.tokens = saved_tokens
            return None
        return parser

    def sequence(self, *parsers):
        def parser():
            saved_tokens = self.tokens.copy()
            results = []
            for p in parsers:
                result = p()
                if result is None:
                    self.tokens = saved_tokens
                    return None
                results.append(result)
            return results
        return parser
    
    def many(self, parser, separator=None):
        def parser_fn():
            results = []
            while True:
                # Try to parse a separator first if we have results already
                if len(results) > 0 and separator is not None:
                    saved_tokens = self.tokens.copy()
                    sep_result = separator()
                    if sep_result is None:
                        self.tokens = saved_tokens
                        break

                saved_tokens = self.tokens.copy()
                result = parser()
                if result is None:
                    self.tokens = saved_tokens
                    break
                    
                results.append(result)
    
            return results
        return parser_fn

    def parse_column_list(self):
        def parser():
            left_paren = self.token_type(TokenType.LEFT_PAREN)()
            if left_paren is None:
                return None
            columns = self.many(self.identifier(), self.delimiter(","))()
            if columns is None:
                return None
            right_paren = self.token_type(TokenType.RIGHT_PAREN)()
            if right_paren is None:
                return None
            return columns
        return parser
    
    def parse_value_list(self):
        def parser():
            left_paren = self.token_type(TokenType.LEFT_PAREN)()
            if left_paren is None:
                return None
            values = self.many(self.literal(), self.delimiter(","))()
            if values is None:
                return None
            right_paren = self.token_type(TokenType.RIGHT_PAREN)()
            if right_paren is None:
                return None
            return values
        return parser
    
    def parse_value_lists(self):
        def parser():
            all_values = []
            first_time = True

            while True:
                saved_tokens = self.tokens.copy()
                value_list = self.parse_value_list()()
                if value_list is None:
                    self.tokens = saved_tokens
                    if first_time:
                        return None
                    break
                all_values.append(value_list)
                first_time = False
                saved_tokens = self.tokens.copy()
                if self.delimiter(";")() is not None:
                    break
                elif self.delimiter(",")() is None:
                    self.tokens = saved_tokens
                    break
            return all_values if all_values else None
        return parser
            

    def parse_create_statement(self) -> Node:
        # If we're here we already know this is a CREATE token
        self.next()

        self.consume_keyword("TABLE")


        table_name = self.consume_identifier("table name")
        table = Table(name=table_name)

        create_stmt = CreateTable(table=table)

 

        self.consume_token_type(TokenType.LEFT_PAREN, "after table name")

        while (self.not_eof() and not self.is_right_paren()):
            column = self.parse_column_def()
            create_stmt.columns.append(column)
            self.consume_delimiter(",")

        self.consume_token_type(TokenType.RIGHT_PAREN)
        self.consume_delimiter(";")
        return create_stmt
    
    def parse_column_def(self) -> ColumnDef:
        column = ColumnDef()


        column.name = self.consume_identifier("column name")


        column.datatype = self.consume_datatype()

        if column.datatype == "VARCHAR" and self.is_left_paren():
            self.next()

            column.datatype += f'({self.consume_literal("for VARCHAR length")})'

            self.consume_token_type(TokenType.RIGHT_PAREN, "after VARCHAR length")

        while (self.not_eof() and not self.is_delimiter() and not self.is_right_paren()):
            if self.consume_keyword_sequence("NOT", "NULL"):
                column.constraints.append("NOT NULL")
            elif self.consume_keyword_sequence("PRIMARY", "KEY"):
                column.constraints.append("PRIMARY KEY")
            else: 
                raise Exception(f"Unexpected token in column definition: {self.curr_token()}")

        return column
    
    def parse_alter_statement(self) -> Node:
        # Current node is ALTER so pop
        self.next()

        self.consume_keyword("TABLE")

        table_name = self.consume_identifier("table name")
        table = Table(name=table_name)
        alter_stmt = AlterTable(table=table)
        alter_stmt.operations = []

        while self.not_eof() and not self.is_semicolon():
            if self.is_keyword():
                if self.curr_value() == 'ADD':
                    self.next()
                    self.consume_keyword("COLUMN")
                    column = self.parse_column_def()
                    operation = AlterOperation(action="ADD", column=column)
                    alter_stmt.operations.append(operation)

                elif self.curr_value() == 'DROP':
                    self.next()
                    self.consume_keyword("COLUMN")
         
                    column_name = self.consume_identifier("column name")
                    column = ColumnDef(name=column_name)
                    operation = AlterOperation(action="DROP", column=column)
                    alter_stmt.operations.append(operation)
                else:
                    self.next()
            if self.is_comma():
                self.next()
            elif not self.is_semicolon():
                raise Exception("Expected comma or semicolon after alter operation")
            
        self.consume_delimiter(";")

        return alter_stmt

    def consume_keyword(self, keyword:str ) -> None:
        if not self.is_keyword() or self.curr_value() != keyword:
            raise Exception(f"Expected {keyword} keyword, got: {self.curr_token()}")
        self.next()

    def consume_delimiter(self, delimiter:str, context: str="" ) -> str:
        if not self.is_delimiter() or self.curr_value() != delimiter:
            raise Exception(f"Expected delimiter{' ' + context if context else ''}, got: {self.curr_token()}")
        return self.next().value

        
    def consume_literal(self, context: str = "") -> str:
        if not self.is_literal():
            raise Exception(f"Expected literal{' ' + context if context else ''}, got: {self.curr_token()}")
        return self.next().value

    def consume_identifier(self, context: str = "") -> str:
        if not self.is_identifier():
            raise Exception(f"Expected identifier{' ' + context if context else ''}, got: {self.curr_token()}")
        return self.next().value
    
    def consume_datatype(self, context: str = "") -> str:
        if not self.is_datatype():
            raise Exception(f"Expected datatype{' ' + context if context else ''}, got: {self.curr_token()}")
        return self.next().value
    
    def consume_token_type(self,  token_type: TokenType, context: str = "") -> Token:
        if self.curr_type() != token_type:
            raise Exception(f"Expected {token_type.name}{' ' + context if context else ''}, got: {self.curr_token()}")
        return self.next()

    def consume_keyword_sequence(self, *keywords) -> bool:
        if self.match_keyword_sequence(*keywords):
            for _ in keywords:
                self.next()
            return True
        return False

    def match_keyword_sequence(self, *keywords) -> bool:
        if len(keywords) > len(self.tokens):
            return False
        for i, keyword in enumerate(keywords):
            if i >= len(self.tokens) or self.tokens[i].type != TokenType.KEYWORD or self.tokens[i].value != keyword:
                return False
        return True


    def check_keyword(self, keyword: str) -> bool:
        return self.is_keyword() and self.curr_value() == keyword
    
    def is_keyword(self) -> bool:
        return self.curr_type() == TokenType.KEYWORD
    
    def is_datatype(self) -> bool:
        return self.curr_type() == TokenType.DATATYPE
    
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
        return self.curr_type() == TokenType.LEFT_PAREN
    
    def is_right_paren(self) -> bool:
        return self.curr_type() == TokenType.RIGHT_PAREN
    
    def curr_value(self) -> str:
        return self.tokens[0].value
    
    def curr_type(self) -> TokenType:
        return self.tokens[0].type
        
    def curr_token(self) -> Token:
        return self.tokens[0]

    def next(self) -> Token:
        return self.tokens.pop(0)




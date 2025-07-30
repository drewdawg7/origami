from abstract_syntax_tree import Node, Schema, ColumnDef, AlterOperation, AlterTable, Table, Insert, ValueLiteral, UpdateCondition, Update, CreateTable
from lexer import TokenType, Token, tokenize
from typing import Any
from pydantic import BaseModel

class ParseResult(BaseModel):
    value: Any = None
    is_useful: bool = False
    is_optional: bool = False

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
       
        update_parser = self.sequence(
            self.keyword("UPDATE"),
            self.identifier(),
            self.keyword("SET"),
            self.identifier(),
            self.equals(),
            self.literal(),
            self.keyword("WHERE"),
            self.identifier(),
            self.equals(),
            self.literal(),
            self.delimiter(";")
        )
        parse_result = update_parser()
        if parse_result.value is None:
            return None
        
        results = parse_result.value
        _, table_name, _, column_name, set_op, value, _, condition_column, condition_op, condition_value, _ = results
        
        update_condition = UpdateCondition(
            column=condition_column, 
            operator=condition_op.value,  # Use the token's value
            value=ValueLiteral(value=condition_value)
        )
        
        # Create and return the update statement
        return Update(
            table_name=table_name,
            columns=[column_name],
            values=[ValueLiteral(value=value)],
            conditions=[update_condition]
        )

    
    
    def parse_insert_statement(self) -> Node:
        insert_parser = self.sequence(
            self.keyword("INSERT"),
            self.keyword("INTO"),
            self.identifier(),
            self.parse_column_list(),
            self.keyword("VALUES"),
            self.parse_value_lists()
        )
        parse_result = insert_parser()
        
        print(f'\nparse_result.value: {parse_result.value}\n')
        if parse_result.value is None:
            return None
        
        # Unpack values from the sequence parse result
        results = parse_result.value
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
            print(f'keyword: {self.curr_token()}')
            if self.is_keyword() and self.curr_value() == expected_word:
                result = self.curr_value()
                self.next()
                return ParseResult(value=result)
            return ParseResult()
        return parser

    def identifier(self):
        def parser():
            print(f'identifier: {self.curr_token()}')
            if self.is_identifier():
                result = self.curr_value()
                self.next()
                return ParseResult(value=result)
            return ParseResult()
        return parser
    
    def literal(self):
        def parser():
            print(f'literal: {self.curr_token()}')
            if self.is_literal():
                result = self.curr_value()
                self.next()
                return ParseResult(value=result)
            return ParseResult()
        return parser
    
    def token_type(self, expected_type):
        def parser():
            print(f'token_type: {self.curr_token()}')
            if self.curr_type() == expected_type:
                result = self.curr_token()
                self.next()
                return ParseResult(value=result)
            return ParseResult()
        return parser
    
    def equals(self):
        def parser():
            if self.is_equals():
                result = self.curr_token()
                self.next()
                return ParseResult(value=result)
            return ParseResult()
        return parser

    def delimiter(self, expected_delimiter):
        def parser():
            print(f'delimiter: {self.curr_token()}')
            if self.is_delimiter() and self.curr_value() == expected_delimiter:
                result = self.curr_token()
                self.next()
                return ParseResult(value=result)
            return ParseResult()
        return parser
    
    def datatype(self):
        def parser():
            if self.is_datatype():
                result = self.curr_token()
                self.next()
                return ParseResult(value=result)
            return ParseResult()
        return parser

    def sequence(self, *parsers):
    
        def parser():
            print(f'sequence: {self.curr_token()}')
            results = []
            for p in parsers:
                parse_result = p()
                if parse_result.value is None and not parse_result.is_optional:
                    return ParseResult()
                
                if parse_result.value is not None:
                    results.append(parse_result.value)
            
            return ParseResult(value=results)
        
        return parser
    
    def many(self, parser, separator=None):
        def parser_fn():
            results = []
            while True:
                # Try to parse a separator first if we have results already
                if len(results) > 0 and separator is not None:
                    sep_result = separator()
                    if sep_result.value is None:
                        break

                result = parser()
                if result.value is None:
                    break
                    
                results.append(result.value)
        
            return ParseResult(value=results if results else None)
        return parser_fn

    def parse_column_list(self):
        def parser():
            column_list_parser = self.sequence(
                self.token_type(TokenType.LEFT_PAREN),
                self.many(self.identifier(), self.delimiter(",")),
                self.token_type(TokenType.RIGHT_PAREN),
            )
            parse_result = column_list_parser()
            if parse_result.value is None:
                return ParseResult
            return ParseResult(value=parse_result.value[1])
        return parser
    
    def parse_value_list(self):
        def parser():
            value_list_parser = self.sequence(
                self.token_type(TokenType.LEFT_PAREN),
                self.many(self.literal(), self.delimiter(",")),
                self.token_type(TokenType.RIGHT_PAREN)
            )
            parse_result = value_list_parser()
            if parse_result.value is None:
                return ParseResult()
            
            return ParseResult(value=parse_result.value[1])
        return parser
    
    def parse_value_lists(self):
        def parser():
            all_values = []
            first_time = True

            while True:
                value_list_result = self.parse_value_list()()
                
                if value_list_result.value is None:
                    if first_time:
                        return ParseResult()
                    break
                
                all_values.append(value_list_result.value)
                first_time = False
                
                semicolon_result = self.delimiter(";")()
                
                if semicolon_result.value is not None:
                    break
                
                comma_result = self.delimiter(",")()
                if comma_result.value is None:
                    break
            
            return ParseResult(value=all_values)
        return parser
                

    def parse_create_statement(self) -> Node:


        #===========================================#
        create_parser = self.sequence(
            self.keyword("CREATE"),
            self.keyword("TABLE"),
            self.identifier(),
            self.token_type(TokenType.LEFT_PAREN),
            self.many(
                self.sequence(
                    self.identifier(),
                    self.datatype(),
                ),
                self.delimiter(",")
            ),
            self.token_type(TokenType.RIGHT_PAREN),
            self.delimiter(";")

        )
        parse_result = create_parser()
        if parse_result.value is None:
            return None
        
        # Unpack values from the sequence parse result
        results = parse_result.value
        _, _, table_name, _, column_data_list, _, _ = results
        
        # Create the table object
        table = Table(name=table_name)
        
        # Create the create table statement
        create_stmt = CreateTable(table=table)
        
        # Process column definitions
        for column_data in column_data_list:
            column_name, datatype_token = column_data
            column = ColumnDef(
                name=column_name,
                datatype=datatype_token.value
            )
            create_stmt.columns.append(column)
        
        return create_stmt
    
    def parse_column_def(self):
        # column = ColumnDef()


        # column.name = self.consume_identifier("column name")


        # column.datatype = self.consume_datatype()

        # if column.datatype == "VARCHAR" and self.is_left_paren():
        #     self.next()

        #     column.datatype += f'({self.consume_literal("for VARCHAR length")})'

        #     self.consume_token_type(TokenType.RIGHT_PAREN, "after VARCHAR length")

        # while (self.not_eof() and not self.is_delimiter() and not self.is_right_paren()):
        #     if self.consume_keyword_sequence("NOT", "NULL"):
        #         column.constraints.append("NOT NULL")
        #     elif self.consume_keyword_sequence("PRIMARY", "KEY"):
        #         column.constraints.append("PRIMARY KEY")
        #     else: 
        #         raise Exception(f"Unexpected token in column definition: {self.curr_token()}")

        #====================================
        column_parser = self.sequence(
            self.identifier(),
            self.datatype(),
        )


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




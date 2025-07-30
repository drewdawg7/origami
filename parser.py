from abstract_syntax_tree import Node, Schema, ColumnDef, AlterOperation, AlterTable, Table, Insert, ValueLiteral, UpdateCondition, Update, CreateTable
from lexer import TokenType, Token, tokenize
from typing import Any
from pydantic import BaseModel

class ParseResult(BaseModel):
    value: Any = None
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
        create_parser = self.sequence(
            self.keyword("CREATE"),
            self.keyword("TABLE"),
            self.identifier(),
            self.token_type(TokenType.LEFT_PAREN),
            self.many(
                self.sequence(
                    self.identifier(),
                    self.datatype(),
                    self.optional(
                        self.sequence(
                            self.token_type(TokenType.LEFT_PAREN),
                            self.literal(),
                            self.token_type(TokenType.RIGHT_PAREN)
                        )
                    ),
                    self.optional(self.many(self.parse_constraint()))
                ),
                self.delimiter(",")
            ),
            self.token_type(TokenType.RIGHT_PAREN),
            self.delimiter(";")
        )
        
        parse_result = create_parser()
        if parse_result.value is None:
            return None
        
        results = parse_result.value
        _, _, table_name, _, column_data_list, _, _ = results
        
        table = Table(name=table_name)
        
        create_stmt = CreateTable(table=table)
        
        for column_data in column_data_list:
            column_name = column_data[0]
            datatype_token = column_data[1]
            
            size_spec = None
            constraints_list = None
            
            for i in range(2, len(column_data)):
                item = column_data[i]
                if isinstance(item, list) and len(item) == 3:
                    size_spec = item[1]  # Get the number part
                elif item is not None:
                    constraints_list = item
            
            datatype_str = datatype_token.value
            if size_spec:
                datatype_str += f"({size_spec})"
                
            column = ColumnDef(
                name=column_name,
                datatype=datatype_str
            )
            
            if constraints_list is not None:
                processed_constraints = []
                for constraint in constraints_list:
                    if isinstance(constraint, list):
                        processed_constraints.append(" ".join(constraint))
                    else:
                        processed_constraints.append(constraint)
                
                column.constraints = processed_constraints
            
            create_stmt.columns.append(column)
        
        return create_stmt
        

    def parse_alter_statement(self) -> Node:


        alter_parser = self.sequence(
            self.keyword("ALTER"),
            self.keyword("TABLE"),
            self.identifier(),

            self.many(
                self.choice(
                    self.sequence(
                        self.keyword("ADD"),
                        self.keyword("COLUMN"),
                        self.identifier(),
                        self.datatype(),
                        self.optional(
                            self.sequence(
                                self.token_type(TokenType.LEFT_PAREN),
                                self.literal(),
                                self.token_type(TokenType.RIGHT_PAREN)
                            )
                        ),
                        self.optional(self.many(self.parse_constraint()))
                    ),
                    self.sequence(
                        self.keyword("DROP"),
                        self.keyword("COLUMN"),
                        self.identifier()
                    )
                ),
                self.delimiter(",")
            ),
            self.delimiter(";")
        )

        parse_result = alter_parser()
        if parse_result.value is None:
            return None
        
        results = parse_result.value
        
        _, _, table_name, column_operations, _ = results
        
        table = Table(name=table_name)
        
        alter_stmt = AlterTable(table=table)
        
        for op_data in column_operations:
            action = op_data[0]
            
            if action == "ADD":
                # Get base information
                _, _, column_name, datatype_token = op_data[:4]
                
                # Check for VARCHAR size specification or constraints
                size_spec = None
                constraints_list = None
                
                # Look through remaining items for size and constraints
                for i in range(4, len(op_data)):
                    item = op_data[i]
                    if isinstance(item, list) and len(item) == 3:
                        # This is likely the size specification: (255)
                        size_spec = item[1]  # Get the number part
                    elif item is not None:
                        # This is likely the constraints list
                        constraints_list = item
                
                # Create the column with the proper datatype
                datatype_str = datatype_token.value
                if size_spec:
                    datatype_str += f"({size_spec})"
                    
                column = ColumnDef(
                    name=column_name,
                    datatype=datatype_str
                )
                
                # Process constraints if present
                if constraints_list is not None:
                    processed_constraints = []
                    for constraint in constraints_list:
                        if isinstance(constraint, list):
                            processed_constraints.append(" ".join(constraint))
                        else:
                            processed_constraints.append(constraint)
                    
                    column.constraints = processed_constraints
            
            elif action == "DROP":
                _, _, column_name = op_data
                
                column = ColumnDef(
                    name=column_name,
                    datatype=""  # No datatype for DROP operations
                )
            
            operation = AlterOperation(action=action, column=column)
            alter_stmt.operations.append(operation)
        
        return alter_stmt

    def optional(self, parser):
        def parser_fn():
            result = parser()
            if result.value is None:
                return ParseResult(value=None, is_optional=True)
            return result
        return parser_fn
    
    def choice(self, *parsers):
        def parser_fn():
            for p in parsers:
                result = p()
                if result.value is not None:
                    return result
            return ParseResult()
        return parser_fn
    def parse_not_null(self):
        return self.sequence(
            self.keyword("NOT"),
            self.keyword("NULL")
        )

    def parse_primary_key(self):
        return self.sequence(
            self.keyword("PRIMARY"),
            self.keyword("KEY")
        )
    def parse_constraint(self):
        return self.choice(
            self.parse_not_null(),
            self.parse_primary_key()
        )
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




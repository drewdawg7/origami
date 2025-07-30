from abstract_syntax_tree import Node, Schema, ColumnDef, AlterOperation, AlterTable, Table, Insert, ValueLiteral, UpdateCondition, Update, CreateTable
from lexer import TokenType, Token, tokenize
from typing import Any, Callable
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
            self.label("table", self.identifier()),
            self.keyword("SET"),
            self.label("col", self.identifier()),
            self.label("op", self.equals()),
            self.label("value", self.literal()),
            self.keyword("WHERE"),
            self.label("cond_col", self.identifier()),
            self.label("cond_op", self.equals()),
            self.label("cond_val", self.literal()),
            self.delimiter(";")
        )
        
        pr = update_parser()
        if pr.value is None:
            return None
            
        tbl   = pr.value["table"]
        col   = pr.value["col"] 
        op    = pr.value["op"].value
        val   = pr.value["value"]
        cc    = pr.value["cond_col"]
        cop   = pr.value["cond_op"].value
        cv    = pr.value["cond_val"]
        
        update_condition = UpdateCondition(
            column=cc,
            operator=cop,
            value=ValueLiteral(value=cv)
        )
        
        # Create and return the update statement
        return Update(
            table_name=tbl,
            columns=[col],
            values=[ValueLiteral(value=val)],
            conditions=[update_condition]
        )
    
        
    def parse_insert_statement(self) -> Node:
        insert_parser = self.sequence(
            self.keyword("INSERT"),
            self.keyword("INTO"),
            self.label("table_name", self.identifier()),
            self.label("columns", self.parse_column_list()),
            self.keyword("VALUES"),
            self.label("values", self.parse_value_lists())
        )
        pr = insert_parser()
        
        if pr.value is None:
            return None
        
        # Extract values using labels
        table_name = pr.value["table_name"]
        columns = pr.value["columns"]
        all_values = pr.value["values"]
        
        # Validate that columns and values have matching lengths
        for values in all_values:
            if len(columns) != len(values):
                raise Exception("Columns and values have mismatched lengths")
            
        # Convert raw values to ValueLiteral objects
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
            merged: dict[str, Any] = {}
            ordered: list[Any] = []
            for p in parsers:
                pr = p()
                if pr.value is None and not pr.is_optional:
                    return ParseResult()               
                if pr.value is None:
                    continue                           
                if isinstance(pr.value, dict):
                    merged.update(pr.value)            
                else:
                    ordered.append(pr.value)           
            return ParseResult(value=merged if merged else ordered)
        return parser
    
    def many(self, parser, separator=None):
        def parser_fn():
            results = []
            while True:
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
            self.label("table_name", self.identifier()),
            self.token_type(TokenType.LEFT_PAREN),
            self.label("columns", self.many(
                self.column(),
                self.delimiter(",")
            )),
            self.token_type(TokenType.RIGHT_PAREN),
            self.delimiter(";")
        )
        
        parse_result = create_parser()
        if parse_result.value is None:
            raise Exception("Error while parsing create statement.")
        
        table_name = parse_result.value["table_name"]
        columns_data = parse_result.value["columns"]
        
        table = Table(name=table_name)
        create_stmt = CreateTable(table=table)
        
        for column in columns_data:
            column_name = column["column_name"]
            datatype_token = column["datatype"]
            
            # Initialize size_spec with a default value
            size_spec = None
            if "size_spec" in column and column["size_spec"] is not None:
                size_spec = column["size_spec"][1] 
            
            datatype_str = datatype_token.value
            if size_spec:
                datatype_str += f"({size_spec})"
                
            column_def = ColumnDef(
                name=column_name,
                datatype=datatype_str
            )
            
            if "constraints" in column and column["constraints"] is not None:
                processed_constraints = []
                for constraint in column["constraints"]:
                    if isinstance(constraint, list):
                        processed_constraints.append(" ".join(constraint))
                    else:
                        processed_constraints.append(constraint)
                
                column_def.constraints = processed_constraints
            
            create_stmt.columns.append(column_def)
        
        return create_stmt
        

    def parse_alter_statement(self) -> Node:
        alter_parser = self.sequence(
            self.keyword("ALTER"),
            self.keyword("TABLE"),
            self.label("table_name", self.identifier()),
            self.label("operations", self.many(
                self.choice(
                    self.sequence(
                        self.label("action", self.keyword("ADD")),
                        self.keyword("COLUMN"),
                        self.column()
                    ),
                    self.sequence(
                        self.label("action", self.keyword("DROP")),
                        self.keyword("COLUMN"),
                        self.label("column_name", self.identifier())
                    )
                ),
                self.delimiter(",")
            )),
            self.delimiter(";")
        )

        pr = alter_parser()
        if pr.value is None:
            return None
        
        # Extract labeled values
        table_name = pr.value["table_name"]
        operations = pr.value["operations"]
        
        # Create the table and alter statement
        table = Table(name=table_name)
        alter_stmt = AlterTable(table=table)
        
        # Process each operation
        for op in operations:
            action = op["action"]
            column_name = op["column_name"]
            
            if action == "ADD":
                datatype_token = op["datatype"]
                
                # Process size specification if present
                size_spec = None
                if "size_spec" in op and op["size_spec"] is not None:
                    size_spec = op["size_spec"][1]  # Get the number part
                
                # Build datatype string
                datatype_str = datatype_token.value
                if size_spec:
                    datatype_str += f"({size_spec})"
                    
                # Create column definition
                column = ColumnDef(
                    name=column_name,
                    datatype=datatype_str
                )
                
                # Process constraints if present
                if "constraints" in op and op["constraints"] is not None:
                    processed_constraints = []
                    for constraint in op["constraints"]:
                        if isinstance(constraint, list):
                            processed_constraints.append(" ".join(constraint))
                        else:
                            processed_constraints.append(constraint)
                    
                    column.constraints = processed_constraints
                    
            elif action == "DROP":
                column = ColumnDef(
                    name=column_name,
                    datatype=""  # No datatype for DROP operations
                )
            
            # Create the operation and add it to the statement
            operation = AlterOperation(action=action, column=column)
            alter_stmt.operations.append(operation)
        
        return alter_stmt

    def column(self):
        return self.sequence(
            self.label("column_name", self.identifier()),
                self.label("datatype", self.datatype()),
                self.optional(
                    self.label("size_spec", self.sequence(
                        self.token_type(TokenType.LEFT_PAREN),
                        self.literal(),
                        self.token_type(TokenType.RIGHT_PAREN)
                    ))
                ),
                self.optional(self.label("constraints", self.many(self.parse_constraint())))
        )
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

    def label(self, name: str, parser: Callable[[], ParseResult]) -> Callable[[], ParseResult]:
        def _p():
            pr = parser()
            if pr.value is None:
                return pr
            return ParseResult(value={name: pr.value}, is_optional=pr.is_optional)
        return _p
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




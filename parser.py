from abstract_syntax_tree import Node, Schema, ColumnDef, AlterOperation, AlterTable, Table, Insert, ValueLiteral, UpdateCondition, Update, CreateTable, ForeignKeyConstraint
from lexer import TokenType, Token, tokenize
from typing import Any, Callable
from pydantic import BaseModel
from base_parser import BaseParser

class ParseResult(BaseModel):
    value: Any = None
    is_optional: bool = False

class Parser(BaseParser):
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
        update_parser = self.update()
        
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
        insert_parser = self.insert()
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
        create_parser = self.create_table()
        
        parse_result = create_parser()
        if parse_result.value is None:
            raise Exception("Error while parsing create statement.")
        
        table_name = parse_result.value["table_name"]
        columns_data = parse_result.value["columns"]
        
        table = Table(name=table_name)
        create_stmt = CreateTable(table=table)
        if "conditional_clause" in parse_result.value and parse_result.value["conditional_clause"] is not None:
            create_stmt.condition_clauses = parse_result.value["conditional_clause"]
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
                print(f"Raw constraints: {column['constraints']}")
                for constraint in column["constraints"]:
                    print(f"Processing constraint: {constraint} (type: {type(constraint)})")
                    if isinstance(constraint, list):
                        processed_constraints.append(" ".join(constraint))
                    else:
                        processed_constraints.append(constraint)
                
                print(f"Processed constraints: {processed_constraints}")
                column_def.constraints = processed_constraints
            
            create_stmt.columns.append(column_def)
        if "constraints" in parse_result.value and parse_result.value["constraints"] is not None:
            for constraint in parse_result.value["constraints"]:
                # Extract the needed components from the constraint sequence
                constraint_name = constraint[1]  # Second element is the identifier after CONSTRAINT
                column_name = constraint[5]      # Column name in parentheses after FOREIGN KEY
                ref_table = constraint[8]        # Referenced table name after REFERENCES
                ref_column = constraint[10]      # Referenced column name in parentheses
                
                # Create the foreign key constraint
                fk_constraint = ForeignKeyConstraint(
                    name=constraint_name,
                    column_name=column_name,
                    referenced_table=ref_table,
                    referenced_column=ref_column
                )
                
                # Add it to the table constraints
                create_stmt.table_constraints.append(fk_constraint)
        return create_stmt
        

    def parse_alter_statement(self) -> Node:
        alter_parser = self.alter_table()

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
                
                size_spec = None
                if "size_spec" in op and op["size_spec"] is not None:
                    size_spec = op["size_spec"][1]  # Get the number part
                
                datatype_str = datatype_token.value
                if size_spec:
                    datatype_str += f"({size_spec})"
                    
                column = ColumnDef(
                    name=column_name,
                    datatype=datatype_str
                )
                
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

   
    

   
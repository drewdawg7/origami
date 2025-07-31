from abstract_syntax_tree import Node, Schema, ColumnDef, AlterOperation, AlterTable, Table, Insert, ValueLiteral, UpdateCondition, Update, CreateTable, ForeignKeyConstraint, PrimaryKeyConstraint
from lexer import TokenType, Token, tokenize
from typing import Any
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
    
    def parse_node(self) -> Node | None:
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
    
    def parse_update_statement(self) -> Node | None:
        update_parser = self.update()
        
        pr:ParseResult = update_parser()
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
    
        
    def parse_insert_statement(self) -> Node | None:
        pr: ParseResult = self.insert()()
        
        if pr.value is None:
            return None
        
        table_name:str = pr.value["table_name"]
        columns = pr.value["columns"]
        all_values = pr.value["values"]
        
        # Validate that columns and values have matching lengths
        for values in all_values:
            if len(columns) != len(values):
                raise Exception("Columns and values have mismatched lengths")
            
        value_literals:list[list[ValueLiteral]] = []
        for val_list in all_values:
            inner_value_literals: list[ValueLiteral] = []
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
            parse_result:ParseResult = column_list_parser()
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
            parse_result:ParseResult = value_list_parser()
            if parse_result.value is None:
                return ParseResult()
            
            return ParseResult(value=parse_result.value[1])
        return parser
    
    def parse_value_lists(self):
        def parser():
            all_values = []
            first_time:bool = True

            while True:
                value_list_result = self.parse_value_list()()
                
                if value_list_result.value is None:
                    if first_time:
                        return ParseResult()
                    break
                
                all_values.append(value_list_result.value)
                first_time: bool = False
                
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
        
        parse_result:ParseResult = create_parser()
        if parse_result.value is None:
            raise Exception("Error while parsing create statement.")
        
        # Debug print to see the structure
        
        table_name = parse_result.value["table_name"]
        table_elements = parse_result.value["table_elements"]
        
        table:Table = Table(name=table_name)
        create_stmt:CreateTable = CreateTable(table=table)
        
        if "conditional_clause" in parse_result.value:
            create_stmt.condition_clauses = parse_result.value["conditional_clause"]
        
        for element in table_elements:
            if "column_name" in element:
                column_name:str = element["column_name"]
                datatype_token = element["datatype"]
                size_spec = element.get("size_spec")
                constraints = element.get("constraints")
                
                column_def:ColumnDef = self.create_column_def(column_name, datatype_token, size_spec, constraints)
                create_stmt.columns.append(column_def)
                
            elif "primary_key_constraint" in element:
                pk_data = element["primary_key_constraint"]
                if "pk_col" in pk_data:
                    pk_col:str = pk_data["pk_col"]["identifier"]
                    pk_constraint:PrimaryKeyConstraint = PrimaryKeyConstraint(column_name=pk_col)
                    create_stmt.table_constraints.append(pk_constraint)
                    
            elif "foreign_key_constraint" in element:
                fk_data = element["foreign_key_constraint"]
                
                constraint_name = fk_data.get("constraint_name")
                column_name = fk_data.get("column_name")
                ref_table = fk_data.get("referenced_table")
                ref_column = fk_data.get("referenced_column")
                
                if all([constraint_name, column_name, ref_table, ref_column]):
                    fk_constraint: ForeignKeyConstraint = ForeignKeyConstraint(
                        name=constraint_name,
                        column_name=column_name,
                        referenced_table=ref_table,
                        referenced_column=ref_column
                    )
                    
                    create_stmt.table_constraints.append(fk_constraint)
        
        return create_stmt
        

    def parse_alter_statement(self) -> Node | None:
        alter_parser = self.alter_table()

        pr = alter_parser()
        if pr.value is None:
            return None
        
        # Extract labeled values
        table_name = pr.value["table_name"]
        operations = pr.value["operations"]
        
        # Create the table and alter statement
        table = Table(name=table_name)
        alter_stmt: AlterTable = AlterTable(table=table)
        
        # Process each operation
        for op in operations:
            if "add_column" in op:
                action = op["add_column"]["action"]
                column_name = op["add_column"]["column_name"]
                datatype_token = op["add_column"]["datatype"]
                size_spec = op["add_column"].get("size_spec")
                constraints = op["add_column"].get("constraints")
                
                column:ColumnDef = self.create_column_def(column_name, datatype_token, size_spec, constraints)
            elif "drop_column" in op:
                action = op["drop_column"]["action"]
                column_name = op["drop_column"]["column_name"]
                column: ColumnDef = ColumnDef(
                    name=column_name,
                    datatype=""  
                )
        
            operation: AlterOperation = AlterOperation(action=action, column=column)
            alter_stmt.operations.append(operation)
        
        return alter_stmt



    def process_constraints(self, constraints) -> list[str]:
        processed_constraints: list[str] = []
        for constraint in constraints:
            if isinstance(constraint, list):
                processed_constraints.append(" ".join(constraint))
            else:
                processed_constraints.append(constraint)
        return processed_constraints

    def create_column_def(self, column_name, datatype_token, size_spec=None, constraints=None) -> ColumnDef:
        datatype_str = datatype_token.value
        if size_spec:
            datatype_str += f"({size_spec})"
            
        column_def:ColumnDef = ColumnDef(
            name=column_name,
            datatype=datatype_str
        )
        
        if constraints:
            column_def.constraints = self.process_constraints(constraints)
        
        return column_def
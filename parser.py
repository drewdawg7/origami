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
        
        table_name = pr.value["table_name"]
        columns = pr.value["columns"]
        all_values = pr.value["values"]
        
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
            value_list_parser = self.sequence(
                self.label("value_lists", 
                    self.many(
                        self.parse_value_list(),
                        self.delimiter(",")
                    )
                ),
                self.delimiter(";")
            )
            
            result = value_list_parser()
            if result.value is None:
                return ParseResult()
            
            return ParseResult(value=result.value["value_lists"])
        
        return parser
                


    def parse_create_statement(self) -> Node:
        create_parser = self.create_table()
        
        parse_result = create_parser()
        if parse_result.value is None:
            raise Exception("Error while parsing create statement.")
        
        
        table_name = parse_result.value["table_name"]
        table_elements = parse_result.value["table_elements"]
        
        table = Table(name=table_name)
        create_stmt = CreateTable(table=table)
        
        if "conditional_clause" in parse_result.value and parse_result.value["conditional_clause"] is not None:
            create_stmt.condition_clauses = parse_result.value["conditional_clause"]
        
        for element in table_elements:
            if "column_name" in element:
                column_name = element["column_name"]
                datatype_token = element["datatype"]
                
                size_spec = None
                if "size" in element:
                    size_spec = element["size"]
                
                datatype_str = datatype_token.value
                if size_spec:
                    datatype_str += f"({size_spec})"
                    
                column_def = ColumnDef(
                    name=column_name,
                    datatype=datatype_str
                )
                
                if "constraints" in element and element["constraints"] is not None:
                    column_def.constraints = element["constraints"]

        
                create_stmt.columns.append(column_def)
                
            elif "primary_key_constraint" in element:
                pk_data = element["primary_key_constraint"]
                if "pk_col" in pk_data:
                    pk_col = pk_data["pk_col"]["identifier"]
                    pk_constraint = PrimaryKeyConstraint(column_name=pk_col)
                    create_stmt.table_constraints.append(pk_constraint)
                    
            elif "foreign_key_constraint" in element:
                fk_data = element["foreign_key_constraint"]
                
                constraint_name = fk_data.get("constraint_name")
                column_name = fk_data.get("column_name")
                ref_table = fk_data.get("referenced_table")
                ref_column = fk_data.get("referenced_column")
                
                if constraint_name and column_name and ref_table and ref_column:
                    fk_constraint = ForeignKeyConstraint(
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
        
        table_name = pr.value["table_name"]
        operations = pr.value["operations"]
        
        table = Table(name=table_name)
        alter_stmt = AlterTable(table=table)
        
        for op in operations:
            action = op["action"]
            column_name = op["column_name"]
            
            if action == "ADD":
                datatype_token = op["datatype"]
                
                size_spec = None
                if "size" in op:
                    size_spec = op["size"]
                
                datatype_str = datatype_token.value
                if size_spec:
                    datatype_str += f"({size_spec})"
                    
                column = ColumnDef(
                    name=column_name,
                    datatype=datatype_str
                )
                
                if "constraints" in op and op["constraints"] is not None:
                    column.constraints = op["constraints"]
            
            elif action == "DROP":
                column = ColumnDef(
                    name=column_name,
                    datatype=""  
                )
        
            operation = AlterOperation(action=action, column=column)
            alter_stmt.operations.append(operation)
        
        return alter_stmt





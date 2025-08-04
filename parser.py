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
         
        
        raise ValueError(f"Unexpected token: {self.curr_token()}")
    
    def parse_update_statement(self) -> Node | None:
        update_parser = self.update()
        
        pr = update_parser()
        if pr.value is None:
            return None
            
        tbl   = pr.value["table"]
        col   = pr.value["col"] 
        op    = pr.value["op"].value
        val   = pr.value["value"]
        

        conditions = []
        for condition in pr.value["conditions"]:
            cc = condition["cond_col"]
            cop = condition["cond_op"].value
            cv = condition["cond_val"]
        
            update_condition = UpdateCondition(
                column=cc,
                operator=cop,
                value=ValueLiteral(value=cv)
            )
            conditions.append(update_condition)
        
        return Update(
            table_name=tbl,
            columns=[col],
            values=[ValueLiteral(value=val)],
            conditions=conditions
        )
    
        
    def parse_insert_statement(self) -> Node | None:
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
                


    def parse_create_statement(self) -> Node | None:
        pr = self.create_table()()
        if pr.value is None:
            return None
        
        table_name = pr.value["table_name"]
        table = Table(name=table_name)
        create_stmt = CreateTable(table=table)
        
        if "conditional_clause" in pr.value:
            create_stmt.condition_clauses = pr.value["conditional_clause"]
        
        for element in pr.value["table_elements"]:
            if "column_name" in element:
                datatype = element["datatype"].value
                if "size_params" in element:
                    params = ",".join([param for param in element["size_params"]])
                    datatype += f"({params})"
            
                
                column = ColumnDef(name=element["column_name"], datatype=datatype)
                
                if "constraints" in element:
                    column.constraints = element["constraints"]
                
                create_stmt.columns.append(column)
                
            elif "primary_key_constraint" in element:
                pk = element["primary_key_constraint"]
                create_stmt.table_constraints.append(
                    PrimaryKeyConstraint(column_name=pk["column_name"])
                )
                
            elif "foreign_key_constraint" in element:
                fk = element["foreign_key_constraint"]
                constraint_name = fk.get("constraint_name", f"fk_{table_name}_{fk['column_name']}")
                create_stmt.table_constraints.append(
                    ForeignKeyConstraint(
                        name=constraint_name,
                        column_name=fk["column_name"],
                        referenced_table=fk["referenced_table"],
                        referenced_column=fk["referenced_column"]
                    )
                )

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
                datatype_str = datatype_token.value

                if "size_params" in op:
                    params = ",".join([param for param in op["size_params"]])
                    datatype_str += f"({params})"
                
            
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





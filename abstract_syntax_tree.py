from enum import Enum
from typing import Annotated, Union, List, Literal
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    SCHEMA = "schema"
    CREATE_TABLE = "create_table"
    ALTER_TABLE = "alter_table"
    INSERT = "insert"
    UPDATE = "update"
    TABLE = "table"
    COLUMN_DEF = "column_def"
    DATATYPE = "datatype"
    CONSTRAINT = "constraint"
    IDENTIFIER = "identifier"
    ALTER_OPERATION = "alter_operation",
    LITERAL = "literal"
    UPDATE_CONDITION = "update_condition",



class Node(BaseModel):
    type: NodeType

class Table(Node):
    type: Literal[NodeType.TABLE] = NodeType.TABLE
    name: str = ""

class ValueLiteral(Node):
    type: Literal[NodeType.LITERAL] = NodeType.LITERAL
    value: str


class ColumnDef(Node):
    type: Literal[NodeType.COLUMN_DEF] = NodeType.COLUMN_DEF
    name: str = ""
    datatype: str = ""
    constraints: List[str] = Field(default_factory=list)

    def sql(self) -> str:
        constraint_str = " ".join(self.constraints)
        if constraint_str:
            return f'{self.name} {self.datatype} {constraint_str}'
        return f'{self.name} {self.datatype}'

class UpdateCondition(Node):
    type: Literal[NodeType.UPDATE_CONDITION] = NodeType.UPDATE_CONDITION
    column: str = ""
    operator: str = ""
    value: ValueLiteral = None

    def sql(self) -> str:
        return f"{self.column} {self.operator} {self.value.value}" 

class Insert(Node):
    type: Literal[NodeType.INSERT] = NodeType.INSERT
    table_name: str = ""
    columns: List[str] = Field(default_factory=list)
    values: List[List[ValueLiteral]] = Field(default_factory=list)

    def sql(self) -> str:
        columns_str = ", ".join(self.columns)
        value_strings = []
        for value_list in self.values:
            value_string = "("
            value_string += ", ".join([val.value for val in value_list ]) + ")"
            value_strings.append(value_string)
        full_value_string = ",\n".join(value_strings)
        if self.columns:
            return f"INSERT INTO {self.table_name} ({columns_str}) VALUES\n{full_value_string};"
        else:
            return f"INSERT INTO {self.table_name} VALUES\n{full_value_string};"

class Update(Node):
    type: Literal[NodeType.UPDATE] = NodeType.UPDATE
    table_name: str = ""
    columns: List[str] = Field(default_factory=list)
    values: List[ValueLiteral] = Field(default_factory=list)
    conditions: List[UpdateCondition] = Field(default_factory=list)

    def sql(self) -> str:
        # Create the SET clause by pairing columns with their values
        set_clauses = []
        for column, value in zip(self.columns, self.values):
            set_clauses.append(f"{column} = {value.value}")
        set_clause = ", ".join(set_clauses)
        
        # Build the basic UPDATE statement
        sql = f"UPDATE {self.table_name}\nSET {set_clause}"
        
        # Add WHERE clause if conditions exist
        if self.conditions:
            conditions_str = " AND ".join([condition.sql() for condition in self.conditions])
            sql += f"\nWHERE {conditions_str}"
        
        return f"{sql};"

class ForeignKeyConstraint(Node):
    type: Literal[NodeType.CONSTRAINT] = NodeType.CONSTRAINT
    name: str | None
    column_name: str
    referenced_table: str
    referenced_column: str

    def sql(self) -> str:
        return f"CONSTRAINT {self.name} FOREIGN KEY ({self.column_name}) REFERENCES {self.referenced_table} ({self.referenced_column})"

class CreateTable(Node):
    type: Literal[NodeType.CREATE_TABLE] = NodeType.CREATE_TABLE
    table: Table = None
    columns: List[ColumnDef] = Field(default_factory=list)
    condition_clauses: List[str] = Field(default_factory=list)
    table_constraints: List[ForeignKeyConstraint] = Field(default_factory=list)


    def sql(self) -> str:
        sql = 'CREATE TABLE '
        if self.condition_clauses:
            conditions = ' '.join(self.condition_clauses)
            sql += f'{conditions} '
            
        sql += f'{self.table.name} (\n'
        column_str = ",\n".join([' ' + col.sql() for col in self.columns])
        sql += column_str
        if self.table_constraints:
            sql += ",\n"
            constraint_str = ",\n".join([' ' + constraint.sql() for constraint in self.table_constraints])
            sql += constraint_str
        sql += "\n);"
        return sql

class AlterOperation(Node):
    type: Literal[NodeType.ALTER_OPERATION] = NodeType.ALTER_OPERATION
    action: str
    column: ColumnDef

    def sql(self) -> str:
        if self.action == "ADD":
            if self.column.constraints:
                return f'{self.action} COLUMN {self.column.name} {self.column.datatype} {" ".join(self.column.constraints)}'
            return f'{self.action} COLUMN {self.column.name} {self.column.datatype}'
        elif self.action == "DROP":
            return f'{self.action} COLUMN {self.column.name}'
        else:
            return f'{self.action} COLUMN {self.column.name}'

class AlterTable(Node):
    type: Literal[NodeType.ALTER_TABLE] = NodeType.ALTER_TABLE
    table: Table = None
    operations: List[AlterOperation] = Field(default_factory=list)

    def sql(self) -> str:
        sql = f'ALTER TABLE {self.table.name}\n'
        op_string = ",\n".join([op.sql() for op in self.operations])

        return sql + op_string + ";"



BodyItem = Annotated[
    Union[CreateTable, Table, ColumnDef, AlterTable], 
    Field(discriminator="type")
]


class Schema(Node):
    type: Literal[NodeType.SCHEMA] = NodeType.SCHEMA
    body: List[BodyItem] = Field(default_factory=list)


    def fold(self) -> 'Schema':
        return self.fold_alter_statements()
    
    def fold_alter_statements(self) -> 'Schema':
        create_tables = {}
        other_statements  = []
        alter_statements = []

        for item in self.body: 
            if item.type == NodeType.CREATE_TABLE:
                create_tables[item.table.name] = item
            elif item.type == NodeType.ALTER_TABLE:
                alter_statements.append(item)
            else:
                other_statements.append(item)

        def fold_alter_into_creates(alter: AlterTable) -> bool:
            table_name = alter.table.name
            if table_name in create_tables:
                for op in alter.operations:
                    if op.action == "ADD":
                        create_tables[table_name].columns.append(op.column)
                    if op.action == "DROP":
                        create_tables[table_name].columns = [
                            col for col in create_tables[table_name].columns
                            if col.name != op.column.name
                        ]
                return True
            return False
    
        remaining_alters = []
        for alter in alter_statements:
            if not fold_alter_into_creates(alter):
                remaining_alters.append(alter)

        if remaining_alters and len(remaining_alters) < len(alter_statements):
            temp_schema = Schema()
            temp_schema = Schema()
            temp_schema.body.extend(list(create_tables.values()))
            temp_schema.body.extend(other_statements)
            temp_schema.body.extend(remaining_alters)
            return temp_schema.fold_alter_statements()

        folded_schema = Schema()
        folded_schema.body.extend(list(create_tables.values()))
        folded_schema.body.extend(other_statements)
        folded_schema.body.extend(remaining_alters)

        return folded_schema

    def __str__(self) -> str:
        return self.model_dump_json(indent=1)
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def sql(self) -> str:
        sql_statements = []
        
        for item in self.body:
            if hasattr(item, 'sql') and callable(getattr(item, 'sql')):
                sql_statements.append(item.sql())
            # Handle items that don't have sql method
            # elif item.type == NodeType.ALTER_TABLE:
            #     for op in item.operations:
            #         if op.action == "ADD":
            #             table_name = item.table.name
            #             column_sql = op.column.sql()
            #             sql_statements.append(f"ALTER TABLE {table_name} ADD COLUMN {column_sql};")
        
        return "\n\n".join(sql_statements)
    

# class Literal(Node):
#     type: NodeType = NodeType.LITERAL
#     value: str = None
from enum import Enum
from pydantic.dataclasses import dataclass
from typing import Annotated, Union, List, Literal
from pydantic_core import to_json
from pydantic import TypeAdapter
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    SCHEMA = "schema"
    CREATE_TABLE = "create_table"
    ALTER_TABLE = "alter_table"
    INSERT = "insert"
    TABLE = "table"
    COLUMN_DEF = "column_def"
    DATATYPE = "datatype"
    CONSTRAINT = "constraint"
    IDENTIFIER = "identifier"
    LITERAL = "literal"



class Node(BaseModel):
    type: NodeType

class Table(Node):
    type: Literal[NodeType.TABLE] = NodeType.TABLE
    name: str = ""


class ColumnDef(Node):
    type: Literal[NodeType.COLUMN_DEF] = NodeType.COLUMN_DEF
    name: str = ""
    datatype: str = ""
    constraints: List[str] = Field(default_factory=list)


class CreateTable(Node):
    type: Literal[NodeType.CREATE_TABLE] = NodeType.CREATE_TABLE
    table: Table = None
    columns: List[ColumnDef] = Field(default_factory=list)


class AlterTable(Node):
    type: Literal[NodeType.ALTER_TABLE] = NodeType.ALTER_TABLE
    table: Table = None
    column: ColumnDef = None
    action: str = ""


BodyItem = Annotated[
    Union[CreateTable, Table, ColumnDef, AlterTable], 
    Field(discriminator="type")
]


class Schema(Node):
    type: Literal[NodeType.SCHEMA] = NodeType.SCHEMA
    body: List[BodyItem] = Field(default_factory=list)

    def __str__(self) -> str:
        return self.model_dump_json(indent=1)
    
    def __repr__(self) -> str:
        return self.__str__()
    

# class Literal(Node):
#     type: NodeType = NodeType.LITERAL
#     value: str = None
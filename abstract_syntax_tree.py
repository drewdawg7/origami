from enum import Enum
from pydantic.dataclasses import dataclass
from typing import List, Optional
from dataclasses import field


NodeType = Enum(
    'NodeType',
    [
        'SCHEMA',
        'CREATE_TABLE',
        'ALTER_TABLE',
        'INSERT',
        'TABLE',
        'COLUMN_DEF',
        'DATATYPE',
        'CONSTRAINT',
        'IDENTIFIER',
        'LITERAL'
    ]
)


@dataclass
class Node:
    type: NodeType

@dataclass
class Schema(Node):
    type: NodeType = NodeType.SCHEMA
    body: list[Node] = field(default_factory=list)
@dataclass
class Table(Node):
    type: NodeType = NodeType.TABLE
    name: str = ""

    def __str__(self) -> str:
        return self.name

@dataclass
class ColumnDef(Node):
    type: NodeType = NodeType.COLUMN_DEF
    name: str = ""
    datatype: str = ""
    constraints: list[str] = None

@dataclass
class CreateTable(Node):
    type: NodeType = NodeType.CREATE_TABLE
    table: Table = None
    columns: list[ColumnDef] = field(default_factory=list)

    def __str__(self) -> str:
        return f'CreateTable: {self.table.name}'

@dataclass
class Literal(Node):
    type: NodeType = NodeType.LITERAL
    value: str = None
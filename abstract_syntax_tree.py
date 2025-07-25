from enum import Enum
from pydantic.dataclasses import dataclass
from typing import List, Optional

NodeType = Enum(
    'NodeType',
    [
        'PROGRAM',
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
class Program(Node):
    type: NodeType = NodeType.PROGRAM
    body: list[Node] = None

@dataclass
class Table(Node):
    type: NodeType = NodeType.TABLE
    name: str = ""

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
    columns: list[ColumnDef] = None

@dataclass
class Literal(Node):
    type: NodeType = NodeType.LITERAL
    value: str = None
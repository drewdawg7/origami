from abstract_syntax_tree import Node, Schema, ColumnDef, AlterOperation, AlterTable, Table, Insert, ValueLiteral, UpdateCondition, Update, CreateTable, ForeignKeyConstraint
from lexer import TokenType, Token, tokenize
from typing import Any, Callable
from pydantic import BaseModel

class ParseResult(BaseModel):
    value: Any = None
    is_optional: bool = False


class BaseParser:
    tokens: list[Token] = []

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


    def label(self, name: str, parser: Callable[[], ParseResult]) -> Callable[[], ParseResult]:
        def _p():
            pr = parser()
            if pr.value is None:
                return pr
            return ParseResult(value={name: pr.value}, is_optional=pr.is_optional)
        return _p

    def keyword(self, expected_word):
        def parser():
            if self.is_keyword() and self.curr_value() == expected_word:
                result = self.curr_value()
                self.next()
                return ParseResult(value=result)
            return ParseResult()
        return parser

    def identifier(self):
        def parser():
            if self.is_identifier():
                result = self.curr_value()
                self.next()
                return ParseResult(value=result)
            return ParseResult()
        return parser
    
    def literal(self):
        def parser():
            if self.is_literal():
                result = self.curr_value()
                self.next()
                return ParseResult(value=result)
            return ParseResult()
        return parser
    
    def token_type(self, expected_type):
        def parser():
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

    def is_keyword(self) -> bool:
        return self.curr_type() == TokenType.KEYWORD
    
    def is_datatype(self) -> bool:
        return self.curr_type() == TokenType.DATATYPE
    
    
    def is_literal(self) -> bool:
        return self.curr_type() == TokenType.LITERAL
    
    def is_equals(self) -> bool:
        return self.curr_type() == TokenType.EQUALS

    def is_identifier(self) -> bool:
        return self.curr_type() == TokenType.IDENTIFIER
    
    
    def is_delimiter(self) -> bool:
        return self.curr_type() == TokenType.DELIMITER
    
    def curr_value(self) -> str:
        return self.tokens[0].value
    
    def curr_type(self) -> TokenType:
        return self.tokens[0].type
        
    def curr_token(self) -> Token:
        return self.tokens[0]

    def next(self) -> Token:
        return self.tokens.pop(0)

    def update(self):
        return self.sequence(
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
    def alter_table(self):
        return self.sequence(
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
    def create_table(self):
        return self.sequence(
            self.keyword("CREATE"),
            self.keyword("TABLE"),
            self.optional(
                self.label(
                    "conditional_clause",
                    self.sequence(
                        self.keyword("IF"),
                        self.keyword("NOT"),
                        self.keyword("EXISTS")
                    )
                )
            ),
            self.label("table_name", self.identifier()),
            self.token_type(TokenType.LEFT_PAREN),
            self.label("table_elements", self.many(
                    self.choice(
                        self.column(),
                        self.label("primary_key_constraint", self.primary_key(in_table_def=True)),
                        self.label("foreign_key_constraint", self.foreign_key())
                    ),
                    self.delimiter(",")
                )),
            self.token_type(TokenType.RIGHT_PAREN),
            self.delimiter(";")
        )

    def insert(self): 
        return self.sequence(
            self.keyword("INSERT"),
            self.keyword("INTO"),
            self.label("table_name", self.identifier()),
            self.label("columns", self.parse_column_list()),
            self.keyword("VALUES"),
            self.label("values", self.parse_value_lists())
        )
    def foreign_key(self):
        return self.sequence(
            self.keyword("CONSTRAINT"),
            self.identifier(),
            self.keyword("FOREIGN"),
            self.keyword("KEY"),
            self.token_type(TokenType.LEFT_PAREN),
            self.identifier(),
            self.token_type(TokenType.RIGHT_PAREN),
            self.keyword("REFERENCES"),
            self.identifier(),
            self.token_type(TokenType.LEFT_PAREN),
            self.identifier(),
            self.token_type(TokenType.RIGHT_PAREN)
        )
    
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
                self.optional(self.label("constraints", self.many(self.constraint())))
        )
    

    def constraint(self):
        return self.choice(
            self.not_null(),
            self.primary_key(),
            self.auto_increment()
        )
    
    def not_null(self):
        return self.sequence(
            self.keyword("NOT"),
            self.keyword("NULL")
        )
    
    def primary_key(self, in_table_def=False):
        if not in_table_def:
            return self.sequence(
                self.keyword("PRIMARY"),
                self.keyword("KEY")
            )
        return self.sequence(
            self.keyword("PRIMARY"),
            self.keyword("KEY"),
            self.label("pk_col", self.wrapped_identifier())

            
        )
    def auto_increment(self):
        return self.keyword("AUTO_INCREMENT")
    
    def wrapped_identifier(self):
        return self.sequence(
            self.token_type(TokenType.LEFT_PAREN),
            self.label("identifier", self.identifier()),
            self.token_type(TokenType.RIGHT_PAREN)
        )

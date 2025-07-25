import os, sqlglot
import sqlglot.expressions as exp
from sqlglot import ErrorLevel
import logging
from sql_classes import *


class Parser: 
    def __init__(self, dialect: str = "mysql"):
        self.dialect = dialect
        self.stmts: list[exp.Expression] = []
        self.dropped_tables = set()  
        self.tables = []
        self.addColumnStatements = []
        self.dropColumnStatements = []
        self.alterTableColumnStatements = []

    def load(self, path: str = "."):
        sql_parts = []
        for fname in os.listdir(path):
            if fname.endswith(".sql"):
                with open(os.path.join(path, fname)) as fh:
                    sql_parts.append(fh.read())
        self.combined_sql = "\n".join(sql_parts)
        return self
    

    def parse_sql_into_statements(self):
        parsed = sqlglot.parse(self.combined_sql, read=self.dialect, error_level=ErrorLevel.IGNORE)
        self.stmts = []
        for node in parsed:
            self.stmts.append(node)

    def parse_sql(self):
        parsed = sqlglot.parse(self.combined_sql, read=self.dialect, error_level=ErrorLevel.IGNORE)
        for node in parsed:
            if (node.key == "create" and node.args.get("kind") == "TABLE"):
                table = Table.create_table_from_node(node)
                self.tables.append(table)
            elif (node.key == "alter" and node.args.get("kind") == "TABLE"):
                atcs = AlterTableColumnStatement.create_statement_from_node(node);
                self.alterTableColumnStatements.append(atcs)
            # elif (node.key == "alter" and node.args.get("kind") == "TABLE" and node.args.get("actions")[0].key == "columndef"):
            #     acs = AddColumnStatement.create_column_from_node(node)
            #     self.addColumnStatements.append(acs)
            
            
                

    def merge(self):
        for atcs in self.alterTableColumnStatements:
            for table in self.tables:
                if table.name == atcs.table_name:
                    table.alter(atcs)
                    
    @staticmethod
    def unbracket(node):
        while isinstance(node, exp.Bracket):
            node = node.this
        return node
    

        # Group statements by type
        use_stmts = []
        create_table_stmts = []
        create_trigger_stmts = []  # New group for triggers
        alter_stmts = []
        insert_stmts = []
        other_stmts = []
        
        # Categorize statements
        for stmt in self.stmts:
            if isinstance(stmt, exp.Use):
                use_stmts.append(stmt)
            elif isinstance(stmt, exp.Create):
                if stmt.args.get("kind") == "TABLE":
                    create_table_stmts.append(stmt)
                elif stmt.args.get("kind") == "TRIGGER":
                    create_trigger_stmts.append(stmt)  # Separate triggers
                else:
                    create_table_stmts.append(stmt)  # Other CREATE statements
            elif isinstance(stmt, exp.Alter):
                alter_stmts.append(stmt)
            elif isinstance(stmt, exp.Insert):
                insert_stmts.append(stmt)
            else:
                other_stmts.append(stmt)
        
        # Order: USE, CREATE TABLE, ALTER, OTHER, CREATE TRIGGER, INSERT
        ordered_stmts = []
        
        # Add USE (only first one)
        if use_stmts:
            sql_text = use_stmts[0].sql(dialect=self.dialect)
            if not sql_text.endswith(";"):
                sql_text += ";"
            ordered_stmts.append(sql_text)
        
        # Format and add CREATE TABLE statements
        for stmt in create_table_stmts:
            sql_text = stmt.sql(dialect=self.dialect, pretty=True)
            if not sql_text.endswith(";"):
                sql_text += ";"
            ordered_stmts.append(sql_text)
        
        # Format and add ALTER statements
        for stmt in alter_stmts:
            sql_text = stmt.sql(dialect=self.dialect)
            if not sql_text.endswith(";"):
                sql_text += ";"
            ordered_stmts.append(sql_text)
        
        # Format and add OTHER statements
        for stmt in other_stmts:
            sql_text = stmt.sql(dialect=self.dialect)
            if not sql_text.endswith(";"):
                sql_text += ";"
            ordered_stmts.append(sql_text)
        
        # Format and add CREATE TRIGGER statements (before INSERT)
        for stmt in create_trigger_stmts:
            sql_text = stmt.sql(dialect=self.dialect)
            ordered_stmts.append(sql_text)
        
        # Format and add INSERT statements (at the end)
        for stmt in insert_stmts:
            sql_text = stmt.sql(dialect=self.dialect)
            if not sql_text.endswith(";"):
                sql_text += ";"
            ordered_stmts.append(sql_text)
        
        return "\n".join(ordered_stmts)
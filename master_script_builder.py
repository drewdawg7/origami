import os, sqlglot
import sqlglot.expressions as exp
from sqlglot import ErrorLevel;
import logging


logging.disable(logging.WARNING)




RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
PLUS_PREFIX = f"{BOLD}{GREEN}[+]{RESET}"
ARROW_PREFIX = f"{BOLD}{CYAN}[>]{RESET}"
EXCLAMATION_PREFIX = f"{BOLD}{RED}[!]{RESET}"


def col_name(expr):
    return expr.this.name.lower()




class Parser:
    def __init__(self, dialect: str = "mysql"):
        self.dialect = dialect
        self.stmts: list[exp.Expression] = []
        self.dropped_tables = set()  # Keep track of dropped tables

    def load(self, path: str = "."):
        sql_parts = []
        for fname in os.listdir(path):
            if fname.endswith(".sql"):
                with open(os.path.join(path, fname)) as fh:
                    sql_parts.append(fh.read())
        combined_sql = "\n".join(sql_parts)

        parsed = sqlglot.parse(combined_sql, read=self.dialect, error_level=ErrorLevel.IGNORE)
        self.stmts = []
        for node in parsed:
            self.stmts.append(self.unbracket(node))
        return self

    def process_drops(self):
        print(f"\t{PLUS_PREFIX} Processing DROP TABLE statements...")
        
        # First pass: Find all DROP TABLE statements
        for i, stmt in enumerate(self.stmts):
            if isinstance(stmt, exp.Drop) and stmt.args.get("kind") == "TABLE":
                table_name = stmt.args["this"].name.lower()
                print(f"\t\t{ARROW_PREFIX} Processing DROP TABLE for: {table_name}")
                self.dropped_tables.add(table_name)
        
        # Remove statements related to dropped tables (including the DROP statements themselves)
        kept_stmts = []
        for stmt in self.stmts:
            # Skip all DROP TABLE statements
            if isinstance(stmt, exp.Drop) and stmt.args.get("kind") == "TABLE":
                print(f"\t\t{ARROW_PREFIX} Removing DROP TABLE statement from output")
                continue
            
            # Skip statements related to dropped tables
            if self.is_related_to_dropped_table(stmt):
                continue
            
            # For CREATE TABLE statements, remove FK constraints to dropped tables
            if isinstance(stmt, exp.Create) and stmt.args.get("kind") == "TABLE":
                self.remove_fk_to_dropped_tables(stmt)
            
            kept_stmts.append(stmt)
        
        self.stmts = kept_stmts
        
        # Post-processing validation: ensure no references to dropped tables remain
        self.post_process_dropped_references()

    def is_related_to_dropped_table(self, stmt):
        """Check if a statement is related to a dropped table."""
        # DROP statements were already processed
        if isinstance(stmt, exp.Drop) and stmt.args.get("kind") == "TABLE":
            return True
        
        # Check CREATE TABLE statement
        if isinstance(stmt, exp.Create) and stmt.args.get("kind") == "TABLE":
            table_name = stmt.this.this.name.lower()
            return table_name in self.dropped_tables
        
        # Check CREATE TRIGGER statement
        if isinstance(stmt, exp.Create) and stmt.args.get("kind") == "TRIGGER":
            # Try to determine which table the trigger is for
            if hasattr(stmt, 'args') and stmt.args.get('on'):
                table_name = stmt.args.get('on').this.name.lower()
                return table_name in self.dropped_tables
        
        # Check ALTER TABLE statement
        if isinstance(stmt, exp.Alter):
            table_name = stmt.this.this.name.lower()
            return table_name in self.dropped_tables
        
        # Check INSERT statement
        if isinstance(stmt, exp.Insert) and hasattr(stmt.this, 'this'):
            table_name = stmt.this.this.name.lower()
            return table_name in self.dropped_tables
        
        # Check UPDATE statement
        if isinstance(stmt, exp.Update):
            table_name = stmt.this.name.lower()
            return table_name in self.dropped_tables
        
        return False
    
    def remove_fk_to_dropped_tables(self, create_stmt):
        """Remove foreign key constraints that reference dropped tables."""
        expressions = create_stmt.this.expressions
        filtered_expressions = []
        
        for expr in expressions:
            skip_expr = False
            
            # Handle standard foreign key expressions
            if isinstance(expr, exp.ForeignKey):
                target_table = expr.args.get("references")
                if target_table and target_table.this.name.lower() in self.dropped_tables:
                    print(f"\t\t{ARROW_PREFIX} Removing FK reference to dropped table: {target_table.this.name}")
                    skip_expr = True
                    
            # Check for FOREIGN KEY references in string representation
            if not skip_expr:
                for dropped_table in self.dropped_tables:
                    expr_str = str(expr).lower()
                    if "foreign key" in expr_str and dropped_table.lower() in expr_str:
                        print(f"\t\t{ARROW_PREFIX} Removing FK reference to dropped table: {dropped_table}")
                        skip_expr = True
                        break
            
            if not skip_expr:
                filtered_expressions.append(expr)
        
        create_stmt.this.set("expressions", filtered_expressions)

    def merge_alters(self):
        print(f"\t{PLUS_PREFIX} Merging ALTER statements into CREATE statements...")
        for create_stmt in self.stmts:                    
            if not isinstance(create_stmt, exp.Create):
                continue
            table_name = create_stmt.this.this.name.lower()

            alter_nodes = []
            for stmt in self.stmts:
                if isinstance(stmt, exp.Alter) and stmt.this.this.name.lower() == table_name:
                    alter_nodes.append(stmt)

            for alter_stmt in alter_nodes:
                for action in self.actions(alter_stmt):
                    # Debug information
                    
                    # Handle the specific "IF NOT EXISTS RATING_ID VARCHAR(36) AFTER CERTIFICATE_ID" case
                    if hasattr(action, 'this') and isinstance(action.this, str) and action.this.lower() == "if not exists":
                        column_name = action.args['expression'].this.name
                        column_type = action.args['expression'].args.get('kind')
                        print(f"\t\t{ARROW_PREFIX} Adding column {column_name} with IF NOT EXISTS")
                        
                        # Create a proper column definition
                        column_def = exp.ColumnDef(
                            this=exp.to_identifier(column_name),
                            kind=column_type
                        )
                        
                        # Add it to the CREATE statement
                        self.add_column(create_stmt, column_def)
                        continue
                        
                    elif isinstance(action, exp.ColumnDef):
                        print(f"\t\t{ARROW_PREFIX} Adding column: {action} to {table_name}")
                        self.add_column(create_stmt, action)


                    elif isinstance(action, exp.Drop):
                        if action.args.get("kind") == "FOREIGN KEY":
                            constraint_name = action.args["this"].this.name.lower()
                            print(f"\t\t{ARROW_PREFIX} Dropping foreign key constraint: {constraint_name} from {table_name}")
                            self.drop_constraint(create_stmt, constraint_name)
                        else:
                            column_name = action.args["this"].name.lower()
                            print(f"\t\t{ARROW_PREFIX} Dropping column: {column_name} from {table_name}")
                            self.drop_column(create_stmt, column_name)



                    elif isinstance(action, exp.AlterColumn):
                        print(f"\t\t{ARROW_PREFIX} Changing column: {action} in {table_name}")
                        self.change_type(create_stmt, action.args["this"].name, action.args["dtype"])


                    elif isinstance(action, exp.AddConstraint):
                        print(f"\t\t{ARROW_PREFIX} Adding constraint: {action} to {table_name}")
                        self.add_constraint(create_stmt, action.args["expressions"])

                    else: 
                        print(f"\t\t{EXCLAMATION_PREFIX} Unknown action: {action}")
                        print(f"\t\t{EXCLAMATION_PREFIX} Action type: {type(action)}")
                        if hasattr(action, 'args'):
                            print(f"\t\t{EXCLAMATION_PREFIX} Action args: {action.args}")

        kept = []
        for stmt in self.stmts:
            if not isinstance(stmt, exp.Alter):
                kept.append(stmt)
        self.stmts = kept

    def merge_updates(self):
        print(f"\t{PLUS_PREFIX} Merging UPDATE statements into INSERT statements...")
        inserts = [stmt for stmt in self.stmts if isinstance(stmt, exp.Insert)]
        updates = [stmt for stmt in self.stmts if isinstance(stmt, exp.Update)]

        for insert in inserts:
            if not isinstance(insert.this, exp.Schema):
                continue

            table = insert.this.this.name.lower()
            col_exprs = insert.this.expressions  # identifiers: id, name, email
            values = insert.args.get("expression")

            if not isinstance(values, exp.Values):
                continue

            col_names = [c.name.lower() for c in col_exprs]
            rows = values.expressions  # list of exp.Tuple

            for update in updates:
                if update.this.name.lower() != table:
                    continue

                where = update.args.get("where")
                if not where or not isinstance(where.this, exp.EQ):
                    continue

                key_col = where.this.left.name.lower()
                key_val = where.this.right.this

                # Add any new columns from SET
                for assignment in update.expressions:
                    col = assignment.this.name.lower()
                    if col not in col_names:
                        col_exprs.append(exp.to_identifier(col))
                        col_names.append(col)
                        for row in rows:
                            row.expressions.append(exp.Null())

                # Apply to matching row
                for row in rows:
                    val_map = dict(zip(col_names, row.expressions))
                    target_val = val_map.get(key_col)
                    if isinstance(target_val, exp.Literal) and target_val.this == key_val:
                        for assignment in update.expressions:
                            val_map[assignment.this.name.lower()] = assignment.expression
                        row.set("expressions", [val_map[c] for c in col_names])

        self.stmts = [stmt for stmt in self.stmts if not isinstance(stmt, exp.Update)]

    def add_constraint(self, create_stmt, expressions):
        """Add constraints to a CREATE TABLE statement, handling complex cases."""
        if not expressions:
            return
        
        # Convert single expression to list for uniform processing
        if not isinstance(expressions, list):
            expressions = [expressions]
        
        for expr in expressions:
            try:
                # For debugging
                print(f"\t\t{ARROW_PREFIX} Adding constraint: {expr}")
                
                # Check if it's a proper constraint or just a string
                if isinstance(expr, str):
                    # Try to parse the string as a constraint
                    parsed_expr = sqlglot.parse_one(expr, read=self.dialect)
                    create_stmt.this.expressions.append(parsed_expr)
                else:
                    # Add the constraint expression directly
                    create_stmt.this.expressions.append(expr)
            except Exception as e:
                print(f"\t\t{EXCLAMATION_PREFIX} Error adding constraint: {e}")
                print(f"\t\t{EXCLAMATION_PREFIX} Constraint expression: {expr}")

    def drop_constraint(self, create_stmt, constraint_name):
        expressions = create_stmt.this.expressions
        for i, item in enumerate(expressions):
            if (isinstance(item, exp.ForeignKey) or isinstance(item, exp.Constraint)) and \
               hasattr(item, 'name') and item.name and item.name.lower() == constraint_name:
                del expressions[i]
                break

    def add_column(self, create_stmt, column_def):
        print(f"\t\t{ARROW_PREFIX} Debug column_def type: {type(column_def)}")
        print(f"\t\t{ARROW_PREFIX} Debug column_def: {column_def}")
        
        column_name = None
        data_type = None
        after_column = None
        
        # Handle the specific "IF NOT EXISTS RATING_ID VARCHAR(36) AFTER CERTIFICATE_ID" format
        if str(column_def).startswith('IF NOT EXISTS '):
            # Extract column name, data type, and AFTER clause from the string representation
            parts = str(column_def).split()
            if len(parts) >= 5:  # IF NOT EXISTS [name] [type]
                column_name = parts[3].lower()
                data_type = parts[4]
                
                # Check for AFTER clause
                if len(parts) >= 7 and parts[5].upper() == 'AFTER':
                    after_column = parts[6].lower()
                    print(f"\t\t{ARROW_PREFIX} Parsed IF NOT EXISTS clause: Column={column_name}, Type={data_type}, After={after_column}")
                else:
                    print(f"\t\t{ARROW_PREFIX} Parsed IF NOT EXISTS clause: Column={column_name}, Type={data_type}")
                
                # Create proper column definition
                new_col_def = exp.ColumnDef(
                    this=exp.to_identifier(parts[3]),  # Column name
                    kind=parts[4]                      # Data type
                )
            else:
                print(f"\t\t{EXCLAMATION_PREFIX} Invalid IF NOT EXISTS clause format: {column_def}")
                return
        else:
            # Standard column definition
            try:
                column_name = col_name(column_def).lower()
                new_col_def = column_def
                
                # Check if there's an AFTER clause in the args
                if hasattr(column_def, 'args') and 'after' in column_def.args:
                    after_column = column_def.args['after'].lower()
            except Exception as e:
                print(f"\t\t{EXCLAMATION_PREFIX} Error extracting column name: {e}")
                return
    
        # Check if the column already exists in the table definition
        seen = set()
        for col in create_stmt.this.expressions:
            if isinstance(col, exp.ColumnDef):
                try:
                    seen.add(col_name(col).lower())
                except:
                    pass  # Skip if we can't get column name
    
        if column_name not in seen:
            # If AFTER is specified, insert the column after the specified column
            if after_column:
                position = -1
                for i, col in enumerate(create_stmt.this.expressions):
                    if isinstance(col, exp.ColumnDef) and col_name(col).lower() == after_column:
                        position = i
                        break
                
                if position >= 0:
                    # Insert after the specified column
                    create_stmt.this.expressions.insert(position + 1, new_col_def)
                    print(f"\t\t{ARROW_PREFIX} Successfully added column {column_name} after {after_column}")
                else:
                    # If the specified column isn't found, add to the end
                    create_stmt.this.expressions.append(new_col_def)
                    print(f"\t\t{ARROW_PREFIX} Column {after_column} not found, added {column_name} at the end")
            else:
                # No AFTER clause, add at the end
                create_stmt.this.expressions.append(new_col_def)
                print(f"\t\t{ARROW_PREFIX} Successfully added column {column_name}")
        else:
            print(f"\t\t{ARROW_PREFIX} Column {column_name} already exists, skipping")

    def drop_column(self, create_stmt, name):
        name = name.lower()
        expressions = create_stmt.this.expressions
        for i, col in enumerate(expressions):
            if col_name(col) == name:
                del expressions[i]
                break

    def change_type(self, create_stmt, name, new_type):
        for col in create_stmt.this.expressions:
            if isinstance(col, exp.ColumnDef) and col_name(col) == name:
                col.set("kind", new_type)


    def process_drops(self):
        print(f"\t{PLUS_PREFIX} Processing DROP TABLE statements...")
        
        # First pass: Find all DROP TABLE statements
        for i, stmt in enumerate(self.stmts):
            if isinstance(stmt, exp.Drop) and stmt.args.get("kind") == "TABLE":
                table_name = stmt.args["this"].name.lower()
                print(f"\t\t{ARROW_PREFIX} Processing DROP TABLE for: {table_name}")
                self.dropped_tables.add(table_name)
        
        # Remove statements related to dropped tables (including the DROP statements themselves)
        kept_stmts = []
        for stmt in self.stmts:
            # Skip all DROP TABLE statements
            if isinstance(stmt, exp.Drop) and stmt.args.get("kind") == "TABLE":
                print(f"\t\t{ARROW_PREFIX} Removing DROP TABLE statement from output")
                continue
            
            # Skip statements related to dropped tables
            if self.is_related_to_dropped_table(stmt):
                continue
            
            # For CREATE TABLE statements, remove FK constraints to dropped tables
            if isinstance(stmt, exp.Create) and stmt.args.get("kind") == "TABLE":
                self.remove_fk_to_dropped_tables(stmt)
            
            kept_stmts.append(stmt)
        
        self.stmts = kept_stmts
        
        # Post-processing validation: ensure no references to dropped tables remain
        self.post_process_dropped_references()

    def post_process_dropped_references(self):
        """Additional pass to find and remove any remaining references to dropped tables."""
        for stmt in self.stmts:
            if isinstance(stmt, exp.Create) and stmt.args.get("kind") == "TABLE":
                table_name = stmt.this.this.name
                # Convert the entire SQL to a string and search for dropped table names
                sql_text = stmt.sql(dialect=self.dialect)
                
                for dropped_table in self.dropped_tables:
                    if dropped_table.lower() in sql_text.lower():
                        print(f"\t\t{EXCLAMATION_PREFIX} WARNING: Table {table_name} may still contain references to dropped table {dropped_table}")
    def to_sql(self):
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
    
    def merge(self):
        self.process_drops()  # Process drops first
        self.merge_alters()
        self.merge_updates()
        return self


    def export(self, outfile: str = "merged.sql"):
        sql_text = self.to_sql()
        with open(outfile, "w", encoding="utf-8") as fh:
            fh.write(sql_text)
        return outfile

    def export_reset_script(self, outfile: str = "reset.sql"):
        # Find all CREATE TABLE statements
        tables = []
        for stmt in self.stmts:
            if isinstance(stmt, exp.Create) and stmt.args.get("kind") == "TABLE":
                table_name = stmt.this.this.name
                tables.append(table_name)
        
        # Reverse the order to handle dependencies properly
        tables.reverse()
        
        # Generate DROP statements
        lines = []
        
        # Start with USE statement
        use_stmts = [stmt for stmt in self.stmts if isinstance(stmt, exp.Use)]
        if use_stmts:
            sql_text = use_stmts[0].sql(dialect=self.dialect)
            if not sql_text.endswith(";"):
                sql_text += ";"
            lines.append(sql_text)
        
        # Add SET FOREIGN_KEY_CHECKS=0 to allow dropping tables with foreign keys
        lines.append("SET FOREIGN_KEY_CHECKS=0;")
        
        # Add DROP statements for each table
        for table in tables:
            lines.append(f"DROP TABLE IF EXISTS {table};")
        
        # Reset FOREIGN_KEY_CHECKS
        lines.append("SET FOREIGN_KEY_CHECKS=1;")
        
        # Write to file
        with open(outfile, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        
        return outfile

    @staticmethod
    def actions(alter_stmt):
        acts = alter_stmt.args.get("actions") or alter_stmt.args.get("expression")
    
        # Handle string parsing for problematic constraint formats
        if isinstance(acts, exp.AddConstraint):
            # If it's already parsed as AddConstraint but has multiple expressions
            if isinstance(acts.args.get("expressions"), list):
                return [exp.AddConstraint(expressions=expr) for expr in acts.args.get("expressions")]
        
            # If it's a single constraint
            return [acts]
    
        # Handle case where SQLGlot parsed multiple constraints as a single action
        if isinstance(acts, exp.Expression) and hasattr(acts, 'sql'):
            sql_text = acts.sql()
            if ',' in sql_text and ('add constraint' in sql_text.lower() or 'foreign key' in sql_text.lower()):
                # This might be multiple constraints improperly parsed as one
                print(f"\t\t{ARROW_PREFIX} Detected multiple constraints in a single action, splitting...")
                # Re-parse as separate actions
                try:
                    # Create a mock ALTER statement for each constraint
                    constraints = []
                    parts = sql_text.split(',')
                    for part in parts:
                        if 'add constraint' in part.lower() or 'foreign key' in part.lower():
                            constraints.append(exp.AddConstraint(expressions=sqlglot.parse_one(part.strip(), read='mysql')))
                    return constraints
                except Exception as e:
                    print(f"\t\t{EXCLAMATION_PREFIX} Error splitting constraints: {e}")
    
        # Handle standard list of actions
        if isinstance(acts, list):
            return acts
        
        # Default: return as a single-item list
        return [acts]

    @staticmethod
    def unbracket(node):
        while isinstance(node, exp.Bracket):
            node = node.this
        return node



try: 
    parser = Parser().load("./scripts_to_merge")
    print(f"{PLUS_PREFIX} Merging SQL files...")
    parser.merge()
    print(f"{PLUS_PREFIX} Exporting merged script...")
    parser.export()
    print(f"{PLUS_PREFIX} Exporting reset script...")
    parser.export_reset_script()
    print(f"{PLUS_PREFIX} Done!")
    print(f"{PLUS_PREFIX} Merged SQL file saved as merged.sql")
    print(f"{PLUS_PREFIX} Reset SQL file saved as reset.sql")
except Exception as e:
    print(f"{EXCLAMATION_PREFIX} Error: {e}")
finally:
    input("Press Enter to exit...")
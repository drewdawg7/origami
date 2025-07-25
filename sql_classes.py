#test

class Table:

    def __init__(self, name):
        self.name = name
        self.columns = []
        self.constraints = []

    def addColumn(self, column):
        self.columns.append(column)

    def addConstraint(self, constraint):
        self.constraints.append(constraint)

    def alter(self, atcs):
        if (atcs.alter_type == "add"):
            self.addColumnFromAlterStatement(atcs) 
        elif (atcs.alter_type == "drop"):
            self.dropColumnFromAlterStatement(atcs)

    def addColumnFromAlterStatement(self, atcs):
        col = Column(atcs.col_name, atcs.col_datatype, [])
        self.columns.append(col)

    def dropColumnFromAlterStatement(self, atcs):
        self.columns = [col for col in self.columns if atcs.col_name != col.name]

    def applyConstraintsToColumns(self):
        for constraint in self.constraints:
            for column in self.columns:
                print(f'Col Name: {column.name}')
                print(f'Constraint Col Name: {constraint.column_name}')
                if constraint.column_name == column.name:
                    print("test")
                    column.addConstraint(constraint)
    @staticmethod
    def create_table_from_node(node):
        table = Table(node.this.this.name)
        for expr in node.this.expressions:
            constraints = []
            if expr.args.get("constraints") != None:
                for constraint in expr.args.get("constraints"):
                    column_name = expr.this.name
                    constraint = Constraint(table.name, column_name, constraint.kind )
                    constraints.append(constraint)
            if expr.key == "primarykey":
                constraint_type = expr.key
                column_name = expr.args.get("expressions")[0].args.get("this")
                print(column_name)
                constraint = Constraint(table.name, column_name, constraint_type)
                table.addConstraint(constraint)
            if expr.this != None:
                column = Column(expr.this.name, expr.kind.this.name, constraints)
                table.addColumn(column)
        table.applyConstraintsToColumns()
        return table

    def __str__(self):
        columns_str = "".join(["  "+ str(col) for col in self.columns])
        return f'{self.name}:\n{columns_str}'


    def __repr__(self):
        return self.__str__()


class Column: 
    def __init__(self, name, datatype, constraints):
        self.name = name
        self.datatype = datatype
        self.constraints = constraints
    

    def addConstraint(self, constraint):
        self.constraints.append(constraint)
    def __str__(self):
        constraints_str = "".join(" " + str(con) for con in self.constraints)
        return f'col_name: {self.name}, datatype: {self.datatype},constraints: [{constraints_str} ]\n'
    
    def __repr__(self):
        return self.__str__()
    



class AlterTableColumnStatement: 
    def __init__(self, col_name,  table_name, alter_type, col_datatype = None):
        self.col_name = col_name
        self.col_datatype = col_datatype
        self.table_name = table_name
        if (alter_type == "columndef"):
            alter_type = "add"
        self.alter_type = alter_type

    @staticmethod
    def create_statement_from_node(node):
        table_name = node.this.this.name
        column_name = node.args.get("actions")[0].this.name
        alter_type = node.args.get("actions")[0].key

        column_datatype = None
        if alter_type != "drop":
            column_datatype = node.args.get("actions")[0].args.get("kind").this.name
        return AlterTableColumnStatement(column_name, table_name, alter_type, column_datatype)

    def __str__(self):
        if self.alter_type == "add":
            return f'Add {self.col_name}:{self.col_datatype} to {self.table_name}'
        elif self.alter_type == "drop":
            return f'Drop {self.col_name} from {self.table_name}'
        else:
            return f'invalid alter type: {self.alter_type}'


    
class Constraint:

    def __init__(self, table_name, column_name, constraint_type):
        self.table_name = table_name
        self.column_name = column_name
        self.constraint_type = constraint_type

    def __str__(self):
        return f'{self.constraint_type}'

    def __repr__(self):
        return self.__str__()
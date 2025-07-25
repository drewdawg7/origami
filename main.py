from parser import *


TEST_SQL="""
CREATE TABLE users (
  id INT,
  name VARCHAR(64),
);
"""

prs = Parser()

val = prs.produce_ast(TEST_SQL)
print(val)
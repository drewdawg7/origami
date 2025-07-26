from parser import *


TEST_SQL="""
CREATE TABLE users (
  id INT NOT NULL,
  name VARCHAR(64),
);

ALTER TABLE users
ADD COLUMN email VARCHAR(64);
"""

prs = Parser()

val = prs.produce_ast(TEST_SQL)
print(val)
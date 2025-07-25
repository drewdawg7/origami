CREATE TABLE users (
  id INT NOT NULL,
  name VARCHAR(64),
  PRIMARY KEY(id)
);

INSERT INTO users (id, name, email) VALUES (1, 'Drew', 'drew@example.com');
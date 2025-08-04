
CREATE TABLE products (
  id INT PRIMARY KEY NOT NULL,
  name VARCHAR(100) NOT NULL,
  price DECIMAL(10,2),
  category VARCHAR(50),
  created_at TIMESTAMP,
  is_available BOOLEAN
);

CREATE TABLE orders (
  order_id INT PRIMARY KEY NOT NULL,
  customer_id INT NOT NULL,
  total DECIMAL(12,2),
  status VARCHAR(20)
);

CREATE TABLE order_items (
  item_id INT PRIMARY KEY NOT NULL,
  order_id INT NOT NULL,
  product_id INT NOT NULL,
  quantity INT,
  FOREIGN KEY (order_id) REFERENCES orders(order_id),
  FOREIGN KEY (product_id) REFERENCES products(id)
);

ALTER TABLE products
ADD COLUMN description TEXT,
ADD COLUMN weight DECIMAL(6,2);

ALTER TABLE orders
ADD COLUMN created_at TIMESTAMP NOT NULL,
DROP COLUMN status;

INSERT INTO products (id, name, price, category) VALUES
  (1, 'Laptop', 999.99, 'Electronics'),
  (2, 'Desk Chair', 249.50, 'Furniture'),
  (3, 'Coffee Mug', 12.99, 'Kitchenware');

INSERT INTO orders (order_id, customer_id, total) VALUES
  (101, 5, 1249.48);

INSERT INTO order_items (item_id, order_id, product_id, quantity) VALUES
  (1001, 101, 1, 1),
  (1002, 101, 3, 2);

UPDATE products
SET price = 1099.99
WHERE id = 1;

UPDATE order_items
SET quantity = 3
WHERE order_id = 101 AND product_id = 3;

UPDATE products
SET is_available = false
WHERE category = 'Electronics';
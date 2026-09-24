
BEGIN;

DROP TABLE IF EXISTS deliveries CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS warehouse_stock CASCADE;
DROP TABLE IF EXISTS warehouses CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS manufacturers CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS tempdb CASCADE;

-- Пользователи системы (клиенты, менеджеры, администраторы)
CREATE TABLE users (
    id_user INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fio VARCHAR(100) NOT NULL,
    login VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('client', 'manager', 'admin'))
);

-- Справочник производителей
CREATE TABLE manufacturers (
    id_manufacturer INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- Справочник категорий товаров
CREATE TABLE categories (
    id_category INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- Товары (гитары и аксессуары)
CREATE TABLE products (
    id_product INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    article VARCHAR(30) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    price NUMERIC(12,2) NOT NULL CHECK (price >= 0),
    manufacturer_id INT NOT NULL REFERENCES manufacturers(id_manufacturer) ON DELETE RESTRICT,
    category_id INT NOT NULL REFERENCES categories(id_category) ON DELETE RESTRICT,
    material VARCHAR(100),
    pickup_type VARCHAR(100),
    strings_count INT,
    fret_count INT,
    color VARCHAR(50)
);

-- Склады
CREATE TABLE warehouses (
    id_warehouse INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address VARCHAR(200) NOT NULL
);

-- Остатки товаров на складах (связь многие-ко-многим)
CREATE TABLE warehouse_stock (
    warehouse_id INT NOT NULL REFERENCES warehouses(id_warehouse) ON DELETE CASCADE,
    product_id INT NOT NULL REFERENCES products(id_product) ON DELETE CASCADE,
    quantity INT NOT NULL CHECK (quantity >= 0),
    PRIMARY KEY (warehouse_id, product_id)
);

-- Клиенты магазина
CREATE TABLE customers (
    id_customer INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fio VARCHAR(100) NOT NULL,
    phone VARCHAR(30),
    email VARCHAR(100),
    address VARCHAR(200)
);

-- Заказы (без дублирования логистики — только суть заказа)
CREATE TABLE orders (
    id_order INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_number VARCHAR(30) UNIQUE NOT NULL,
    customer_id INT NOT NULL REFERENCES customers(id_customer) ON DELETE RESTRICT,
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(30) NOT NULL CHECK (status IN ('В обработке','Собран','Передан курьеру','Запланирован','Доставлен','Отменен'))
);

-- Позиции заказов (связь заказ-товар с количеством и ценой на момент заказа)
CREATE TABLE order_items (
    id_order_item INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(id_order) ON DELETE CASCADE,
    product_id INT NOT NULL REFERENCES products(id_product) ON DELETE RESTRICT,
    quantity INT NOT NULL CHECK (quantity > 0),
    price NUMERIC(12,2) NOT NULL CHECK (price >= 0)
);

-- Доставка (расширенная логистика, привязана к заказу 1:1)
CREATE TABLE deliveries (
    id_delivery INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id INT UNIQUE NOT NULL REFERENCES orders(id_order) ON DELETE CASCADE,
    delivery_date DATE,
    address VARCHAR(200) NOT NULL,
    status VARCHAR(30) NOT NULL CHECK (status IN ('В обработке','Собран','Передан курьеру','Запланирован','Доставлен','Отменен'))
);


COMMENT ON TABLE users IS 'Пользователи системы (клиенты, менеджеры, администраторы)';
COMMENT ON TABLE manufacturers IS 'Справочник производителей гитар';
COMMENT ON TABLE categories IS 'Справочник категорий товаров';
COMMENT ON TABLE products IS 'Товары магазина (гитары и аксессуары)';
COMMENT ON TABLE warehouses IS 'Склады магазина';
COMMENT ON TABLE warehouse_stock IS 'Остатки товаров на складах';
COMMENT ON TABLE customers IS 'Клиенты магазина';
COMMENT ON TABLE orders IS 'Заказы клиентов';
COMMENT ON TABLE order_items IS 'Позиции заказов';
COMMENT ON TABLE deliveries IS 'Информация о доставке заказов';


INSERT INTO manufacturers (name) VALUES
('Fender'), ('Gibson'), ('Yamaha'), ('Ibanez'), ('Epiphone'), ('Cort');

INSERT INTO categories (name) VALUES
('Электрогитара'), ('Акустическая гитара'), ('Классическая гитара'),
('Бас-гитара'), ('Аксессуары');

INSERT INTO users (fio, login, password_hash, role) VALUES
('Анна Менеджерова', 'manager', 'demo_hash_manager', 'manager'),
('Иван Администратор', 'admin', 'demo_hash_admin', 'admin'),
('Покупатель Тестовый', 'client', 'demo_hash_client', 'client');

INSERT INTO warehouses (name, address) VALUES
('Основной склад', 'Stockholm, Industrigatan 10'),
('Торговый зал', 'Stockholm, Sveavägen 30');

INSERT INTO customers (fio, phone, email, address) VALUES
('Алексей Смирнов', '+46 70 111 22 33', 'alex@example.com', 'Stockholm, Sveavägen 12'),
('Мария Иванова', '+46 70 222 33 44', 'maria@example.com', 'Stockholm, Odengatan 45'),
('Иван Петров', '+46 70 333 44 55', 'ivan@example.com', 'Uppsala, Kungsgatan 8'),
('Елена Соколова', '+46 70 444 55 66', 'elena@example.com', 'Stockholm, Hornsgatan 21'),
('Дмитрий Волков', '+46 70 555 66 77', 'dmitry@example.com', 'Stockholm, Fleminggatan 7');



CREATE TEMP TABLE tempdb (
    article VARCHAR(30),
    name VARCHAR(200),
    price NUMERIC(12,2),
    manufacturer VARCHAR(100),
    category VARCHAR(100),
    material VARCHAR(100),
    pickup_type VARCHAR(100),
    strings_count INT,
    fret_count INT,
    color VARCHAR(50)
);

\COPY tempdb FROM 'C:\Users\Alexey\Downloads\bd_project\BD\products.csv' DELIMITER ',' CSV HEADER;

INSERT INTO manufacturers (name)
SELECT DISTINCT manufacturer FROM tempdb
WHERE manufacturer IS NOT NULL
ON CONFLICT (name) DO NOTHING;

INSERT INTO categories (name)
SELECT DISTINCT category FROM tempdb
WHERE category IS NOT NULL
ON CONFLICT (name) DO NOTHING;

INSERT INTO products
(article, name, price, manufacturer_id, category_id,
 material, pickup_type, strings_count, fret_count, color)
SELECT
    t.article,
    t.name,
    t.price,
    m.id_manufacturer,
    c.id_category,
    t.material,
    t.pickup_type,
    t.strings_count,
    t.fret_count,
    t.color
FROM tempdb t
INNER JOIN manufacturers m ON m.name = t.manufacturer
INNER JOIN categories c ON c.name = t.category
ON CONFLICT (article) DO NOTHING;

DROP TABLE tempdb;

INSERT INTO warehouse_stock (warehouse_id, product_id, quantity) VALUES
(1,1,3),(2,1,1),(1,2,1),(2,2,1),(1,3,6),(2,3,2),(1,4,2),(2,4,1),
(1,5,4),(2,5,2),(1,6,3),(2,6,2),(1,7,5),(2,7,2),(1,8,7),(2,8,3),
(1,9,1),(2,9,1),(1,10,3),(2,10,1),(1,11,6),(2,11,3),(1,12,1),(2,12,1);

INSERT INTO orders
(order_number, customer_id, order_date, status) VALUES
('ORD-1001',1,'2026-09-15','Доставлен'),
('ORD-1002',2,'2026-09-15','В обработке'),
('ORD-1003',3,'2026-09-16','Доставлен'),
('ORD-1004',4,'2026-09-17','Передан курьеру'),
('ORD-1005',5,'2026-09-17','Запланирован'),
('ORD-1006',1,'2026-09-18','Запланирован');

INSERT INTO order_items (order_id, product_id, quantity, price) VALUES
(1,1,1,89990),(2,2,1,239990),(3,3,2,44990),(4,4,1,129990),
(5,5,1,37990),(6,6,1,45990);

INSERT INTO deliveries (order_id, delivery_date, address, status) VALUES
(1,'2026-09-17','Stockholm, Sveavägen 12','Доставлен'),
(2,NULL,'Stockholm, Odengatan 45','В обработке'),
(3,'2026-09-18','Uppsala, Kungsgatan 8','Доставлен'),
(4,NULL,'Stockholm, Hornsgatan 21','Передан курьеру'),
(5,'2026-09-20','Stockholm, Fleminggatan 7','Запланирован'),
(6,'2026-09-21','Västerås, Stora Gatan 3','Запланирован');

SELECT 'users' AS table_name, COUNT(*) FROM users
UNION ALL SELECT 'manufacturers', COUNT(*) FROM manufacturers
UNION ALL SELECT 'categories', COUNT(*) FROM categories
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'warehouses', COUNT(*) FROM warehouses
UNION ALL SELECT 'warehouse_stock', COUNT(*) FROM warehouse_stock
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'deliveries', COUNT(*) FROM deliveries;


ALTER TABLE customers
ADD COLUMN user_id INT UNIQUE REFERENCES users(id_user) ON DELETE SET NULL;

COMMIT;
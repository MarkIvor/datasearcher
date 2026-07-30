-- DataSearcher Demo: PostgreSQL e-commerce база
-- 4 таблицы: customers, products, orders, order_items
-- Содержит PII (email, телефон) для демонстрации маскирования

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE,
    phone VARCHAR(20),
    city VARCHAR(50),
    age INTEGER,
    registered_at DATE,
    segment VARCHAR(20) DEFAULT 'standard'
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(50),
    price NUMERIC(10, 2),
    stock INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    order_date TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending',
    total_amount NUMERIC(12, 2),
    payment_method VARCHAR(20),
    region VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER,
    unit_price NUMERIC(10, 2),
    discount NUMERIC(5, 2) DEFAULT 0
);

-- ── Данные: 12 клиентов (с PII) ──
INSERT INTO customers (name, email, phone, city, age, registered_at, segment) VALUES
('Анна Иванова', 'anna.ivanova@example.com', '+7(915)123-45-67', 'Москва', 34, '2023-01-15', 'premium'),
('Борис Петров', 'boris.petrov@mail.ru', '+7(916)234-56-78', 'Санкт-Петербург', 45, '2023-02-20', 'standard'),
('Виктория Сидорова', 'vika.sidorova@company.org', '+7(917)345-67-89', 'Москва', 28, '2023-03-10', 'premium'),
('Григорий Смирнов', 'grigory.smirnov@gmail.com', '+7(918)456-78-90', 'Казань', 52, '2023-04-05', 'standard'),
('Дарья Кузнецова', 'darya.kuznetsova@yandex.ru', '+7(919)567-89-01', 'Екатеринбург', 31, '2023-05-12', 'standard'),
('Евгений Попов', 'evgeny.popov@example.com', '+7(920)678-90-12', 'Москва', 41, '2023-06-18', 'premium'),
('Жанна Васильева', 'zhanna.vasileva@mail.ru', '+7(921)789-01-23', 'Новосибирск', 38, '2023-07-22', 'standard'),
('Захар Михайлов', 'zakhar.mikhailov@company.org', '+7(922)890-12-34', 'Санкт-Петербург', 29, '2023-08-30', 'standard'),
('Ирина Соколова', 'irina.sokolova@gmail.com', '+7(923)901-23-45', 'Москва', 47, '2023-09-14', 'premium'),
('Кирилл Новиков', 'kirill.novikov@yandex.ru', '+7(924)012-34-56', 'Казань', 33, '2023-10-25', 'standard'),
('Лариса Фёдорова', 'larisa.fedorova@example.com', '+7(925)123-45-67', 'Екатеринбург', 26, '2023-11-08', 'standard'),
('Михаил Морозов', 'mikhail.morozov@mail.ru', '+7(926)234-56-78', 'Москва', 55, '2023-12-19', 'premium');

-- ── Данные: 15 товаров ──
INSERT INTO products (name, category, price, stock, created_at) VALUES
('iPhone 15 Pro', 'electronics', 119990.00, 25, '2023-09-01'),
('Samsung Galaxy S24', 'electronics', 89990.00, 40, '2023-09-15'),
('MacBook Air M3', 'electronics', 134990.00, 15, '2023-10-01'),
('AirPods Pro 2', 'electronics', 24990.00, 100, '2023-09-22'),
('Кофемашина DeLonghi', 'appliances', 45990.00, 8, '2023-08-10'),
('Пылесос Dyson V15', 'appliances', 59990.00, 12, '2023-07-15'),
('Куртка зимняя Columbia', 'clothing', 18990.00, 30, '2023-10-05'),
('Кроссовки Nike Air', 'clothing', 12990.00, 50, '2023-06-20'),
('Рюкзак Thule SubRail', 'clothing', 9990.00, 25, '2023-05-12'),
('Книга "Грокаем алгоритмы"', 'books', 1290.00, 200, '2023-03-01'),
('Книга "Чистый код"', 'books', 2490.00, 150, '2023-04-15'),
('Наушники Sony WH-1000XM5', 'electronics', 34990.00, 35, '2023-08-25'),
('Чайник Bosch', 'appliances', 4990.00, 80, '2023-02-10'),
('Шарф шерстяной', 'clothing', 2990.00, 60, '2023-10-20'),
('Ноутбук ASUS ZenBook', 'electronics', 89990.00, 18, '2023-11-01');

-- ── Данные: 25 заказов (разные регионы/статусы/методы оплаты) ──
INSERT INTO orders (customer_id, order_date, status, total_amount, payment_method, region) VALUES
(1, '2024-01-15 10:30:00', 'completed', 144980.00, 'card', 'Москва'),
(2, '2024-01-18 14:20:00', 'completed', 89990.00, 'card', 'Санкт-Петербург'),
(3, '2024-02-03 09:15:00', 'completed', 159980.00, 'card', 'Москва'),
(4, '2024-02-14 16:45:00', 'completed', 18990.00, 'cash', 'Казань'),
(5, '2024-02-22 11:00:00', 'cancelled', 4990.00, 'card', 'Екатеринбург'),
(6, '2024-03-01 13:30:00', 'completed', 59990.00, 'card', 'Москва'),
(7, '2024-03-08 17:20:00', 'completed', 24990.00, 'sbp', 'Новосибирск'),
(8, '2024-03-15 10:10:00', 'pending', 12990.00, 'card', 'Санкт-Петербург'),
(1, '2024-03-20 15:45:00', 'completed', 9990.00, 'sbp', 'Москва'),
(9, '2024-04-02 12:00:00', 'completed', 34990.00, 'card', 'Москва'),
(10, '2024-04-10 09:30:00', 'completed', 1290.00, 'cash', 'Казань'),
(11, '2024-04-18 18:15:00', 'cancelled', 2990.00, 'card', 'Екатеринбург'),
(12, '2024-04-25 14:40:00', 'completed', 134990.00, 'card', 'Москва'),
(2, '2024-05-03 11:25:00', 'completed', 4990.00, 'sbp', 'Санкт-Петербург'),
(3, '2024-05-12 16:50:00', 'completed', 45990.00, 'card', 'Москва'),
(4, '2024-05-20 10:05:00', 'pending', 59990.00, 'card', 'Казань'),
(5, '2024-05-28 13:35:00', 'completed', 12990.00, 'card', 'Екатеринбург'),
(6, '2024-06-05 15:20:00', 'completed', 2490.00, 'cash', 'Москва'),
(7, '2024-06-12 09:40:00', 'completed', 89990.00, 'card', 'Новосибирск'),
(8, '2024-06-20 14:15:00', 'cancelled', 34990.00, 'card', 'Санкт-Петербург'),
(9, '2024-07-01 11:50:00', 'completed', 119990.00, 'card', 'Москва'),
(10, '2024-07-08 17:30:00', 'pending', 9990.00, 'sbp', 'Казань'),
(11, '2024-07-15 10:25:00', 'completed', 4990.00, 'cash', 'Екатеринбург'),
(12, '2024-07-22 16:00:00', 'completed', 134990.00, 'card', 'Москва'),
(1, '2024-07-30 12:45:00', 'completed', 24990.00, 'card', 'Москва');

-- ── Данные: 50 позиций в заказах ──
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount) VALUES
(1, 1, 1, 119990.00, 0), (1, 4, 1, 24990.00, 0),
(2, 2, 1, 89990.00, 0),
(3, 3, 1, 134990.00, 0), (3, 4, 1, 24990.00, 0),
(4, 7, 1, 18990.00, 0),
(6, 6, 1, 59990.00, 0),
(7, 4, 1, 24990.00, 0),
(9, 9, 1, 9990.00, 0),
(10, 12, 1, 34990.00, 0),
(11, 10, 1, 1290.00, 0),
(12, 3, 1, 134990.00, 0),
(13, 13, 1, 4990.00, 0),
(14, 5, 1, 45990.00, 0),
(15, 6, 1, 59990.00, 0),
(16, 8, 1, 12990.00, 0),
(17, 11, 1, 2490.00, 0),
(18, 2, 1, 89990.00, 0),
(19, 1, 1, 119990.00, 0),
(20, 9, 1, 9990.00, 0),
(21, 13, 1, 4990.00, 0),
(22, 3, 1, 134990.00, 0),
(23, 4, 1, 24990.00, 0),
(24, 15, 1, 89990.00, 0),
(25, 12, 1, 34990.00, 0),
-- дополнительные позиции для разнообразия
(1, 10, 2, 1290.00, 5.0),
(3, 11, 1, 2490.00, 0),
(6, 13, 2, 4990.00, 10.0),
(10, 10, 3, 1290.00, 0),
(14, 7, 1, 18990.00, 0),
(15, 8, 2, 12990.00, 5.0),
(18, 14, 1, 2990.00, 0),
(19, 4, 1, 24990.00, 0),
(22, 5, 1, 45990.00, 0),
(24, 6, 1, 59990.00, 0),
(25, 9, 1, 9990.00, 0),
(2, 4, 1, 24990.00, 0),
(4, 10, 1, 1290.00, 0),
(7, 10, 2, 1290.00, 0),
(9, 11, 1, 2490.00, 0),
(11, 4, 1, 24990.00, 0),
(13, 10, 2, 1290.00, 0),
(16, 7, 1, 18990.00, 0),
(17, 8, 1, 12990.00, 0),
(20, 11, 1, 2490.00, 0),
(21, 4, 1, 24990.00, 0),
(23, 1, 1, 119990.00, 0),
(8, 8, 1, 12990.00, 0),
(5, 13, 1, 4990.00, 0),
(12, 4, 1, 24990.00, 0);

-- Создадим индексы для тестирования query_explain
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

-- Аналитический view для проверки federated/dump режимов
CREATE OR REPLACE VIEW v_monthly_sales AS
SELECT
    DATE_TRUNC('month', o.order_date) AS month,
    o.region,
    COUNT(*) AS orders_count,
    SUM(o.total_amount) AS revenue,
    AVG(o.total_amount) AS avg_order
FROM orders o
WHERE o.status = 'completed'
GROUP BY 1, 2
ORDER BY 1 DESC, 2;
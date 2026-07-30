-- DataSearcher Demo: MySQL CRM база
-- 3 таблицы: managers, deals, interactions
-- Демонстрирует JOIN с PostgreSQL (clients) через federated режим

CREATE TABLE IF NOT EXISTS managers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(150),
    department VARCHAR(50),
    hire_date DATE,
    rating DECIMAL(3, 2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS deals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manager_id INT,
    client_email VARCHAR(150),
    deal_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    stage VARCHAR(30) DEFAULT 'lead',
    amount DECIMAL(12, 2),
    probability INT DEFAULT 50,
    source VARCHAR(30)
);

CREATE TABLE IF NOT EXISTS interactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    deal_id INT,
    interaction_type VARCHAR(20),
    interaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    duration_minutes INT
);

-- ── Менеджеры (8) ──
INSERT INTO managers (full_name, email, department, hire_date, rating, is_active) VALUES
('Алексей Смирнов', 'a.smirnov@crm.company', 'Sales', '2022-03-15', 4.70, TRUE),
('Мария Иванова', 'm.ivanova@crm.company', 'Sales', '2022-06-20', 4.50, TRUE),
('Дмитрий Козлов', 'd.kozlov@crm.company', 'Sales', '2021-11-10', 4.20, TRUE),
('Ольга Новикова', 'o.novikova@crm.company', 'Sales', '2023-01-25', 4.80, TRUE),
('Сергей Волков', 's.volkov@crm.company', 'Sales', '2022-09-01', 3.90, TRUE),
('Екатерина Зайцева', 'e.zaitseva@crm.company', 'Marketing', '2023-04-12', 4.60, TRUE),
('Павел Лебедев', 'p.lebedev@crm.company', 'Sales', '2021-05-30', 4.10, FALSE),
('Наталья Орлова', 'n.orlova@crm.company', 'Sales', '2023-07-18', 4.90, TRUE);

-- ── Сделки (30) — email клиентов совпадает с PostgreSQL для демо JOIN ──
INSERT INTO deals (manager_id, client_email, deal_date, stage, amount, probability, source) VALUES
(1, 'anna.ivanova@example.com', '2024-01-20 10:00:00', 'won', 150000.00, 100, 'website'),
(1, 'boris.petrov@mail.ru', '2024-01-25 14:30:00', 'won', 95000.00, 100, 'call'),
(2, 'vika.sidorova@company.org', '2024-02-05 11:15:00', 'won', 180000.00, 100, 'website'),
(2, 'grigory.smirnov@gmail.com', '2024-02-18 16:00:00', 'lost', 0.00, 0, 'referral'),
(3, 'darya.kuznetsova@yandex.ru', '2024-03-02 09:45:00', 'won', 75000.00, 100, 'email'),
(3, 'evgeny.popov@example.com', '2024-03-12 13:20:00', 'negotiation', 120000.00, 70, 'website'),
(4, 'zhanna.vasileva@mail.ru', '2024-03-22 15:30:00', 'won', 65000.00, 100, 'call'),
(4, 'zakhar.mikhailov@company.org', '2024-04-01 10:10:00', 'qualified', 45000.00, 40, 'website'),
(1, 'irina.sokolova@gmail.com', '2024-04-10 17:00:00', 'won', 220000.00, 100, 'referral'),
(2, 'kirill.novikov@yandex.ru', '2024-04-20 12:25:00', 'negotiation', 95000.00, 60, 'email'),
(5, 'larisa.fedorova@example.com', '2024-05-05 14:50:00', 'lost', 0.00, 0, 'website'),
(5, 'mikhail.morozov@mail.ru', '2024-05-15 11:40:00', 'won', 310000.00, 100, 'call'),
(6, 'anna.ivanova@example.com', '2024-05-25 09:00:00', 'won', 85000.00, 100, 'email'),
(6, 'vika.sidorova@company.org', '2024-06-03 16:15:00', 'qualified', 55000.00, 50, 'website'),
(3, 'evgeny.popov@example.com', '2024-06-12 10:30:00', 'won', 140000.00, 100, 'referral'),
(4, 'darya.kuznetsova@yandex.ru', '2024-06-22 15:00:00', 'negotiation', 70000.00, 65, 'call'),
(1, 'grigory.smirnov@gmail.com', '2024-07-01 13:10:00', 'won', 110000.00, 100, 'website'),
(2, 'irina.sokolova@gmail.com', '2024-07-10 11:55:00', 'won', 195000.00, 100, 'email'),
(5, 'kirill.novikov@yandex.ru', '2024-07-20 14:35:00', 'lost', 0.00, 0, 'call'),
(6, 'larisa.fedorova@example.com', '2024-08-01 10:20:00', 'qualified', 60000.00, 45, 'website'),
(3, 'mikhail.morozov@mail.ru', '2024-08-10 16:45:00', 'won', 280000.00, 100, 'referral'),
(4, 'anna.ivanova@example.com', '2024-08-20 09:30:00', 'negotiation', 95000.00, 70, 'email'),
(1, 'boris.petrov@mail.ru', '2024-09-01 12:00:00', 'won', 105000.00, 100, 'website'),
(2, 'zhanna.vasileva@mail.ru', '2024-09-12 15:25:00', 'qualified', 50000.00, 40, 'call'),
(5, 'zakhar.mikhailov@company.org', '2024-09-22 11:10:00', 'lost', 0.00, 0, 'email'),
(6, 'evgeny.popov@example.com', '2024-10-02 14:40:00', 'won', 165000.00, 100, 'website'),
(3, 'vika.sidorova@company.org', '2024-10-12 10:55:00', 'negotiation', 130000.00, 75, 'referral'),
(4, 'irina.sokolova@gmail.com', '2024-10-22 16:20:00', 'won', 240000.00, 100, 'call'),
(1, 'darya.kuznetsova@yandex.ru', '2024-11-01 09:15:00', 'qualified', 80000.00, 55, 'email'),
(2, 'mikhail.morozov@mail.ru', '2024-11-12 13:30:00', 'won', 290000.00, 100, 'website');

-- ── Взаимодействия (40) ──
INSERT INTO interactions (deal_id, interaction_type, interaction_date, notes, duration_minutes) VALUES
(1, 'call', '2024-01-18 10:30:00', 'Первый контакт, заинтересован в премиум-пакете', 25),
(1, 'meeting', '2024-01-19 14:00:00', 'Презентация продукта, демо', 60),
(1, 'email', '2024-01-20 09:00:00', 'Отправлено КП', 5),
(2, 'call', '2024-01-23 11:00:00', 'Обсуждение условий', 20),
(2, 'email', '2024-01-24 15:00:00', 'Договор подписан', 5),
(3, 'call', '2024-02-03 10:00:00', 'Клиент из PB, срочная сделка', 30),
(3, 'meeting', '2024-02-04 13:00:00', 'Встреча в офисе', 90),
(4, 'call', '2024-02-17 14:00:00', 'Клиент отказался, дорого', 15),
(5, 'email', '2024-03-01 10:00:00', 'Возврат после отказа', 5),
(5, 'call', '2024-03-02 09:30:00', 'Согласован объём', 20),
(6, 'meeting', '2024-03-10 11:00:00', 'Презентация для команды', 75),
(6, 'call', '2024-03-11 15:00:00', 'Согласование цены', 25),
(7, 'call', '2024-03-20 14:00:00', 'Квалификация лида', 20),
(8, 'email', '2024-04-01 10:00:00', 'Отправлен прайс', 5),
(9, 'meeting', '2024-04-08 16:00:00', 'Большая презентация, VIP-клиент', 120),
(9, 'call', '2024-04-09 10:00:00', 'Подписание договора', 30),
(10, 'call', '2024-04-19 11:30:00', 'Обсуждение сроков', 20),
(11, 'email', '2024-05-04 09:00:00', 'Клиент не ответил', 5),
(12, 'meeting', '2024-05-14 15:00:00', 'Презентация Enterprise-плана', 90),
(12, 'call', '2024-05-15 11:00:00', 'Финальное согласование', 35),
(13, 'email', '2024-05-24 10:00:00', 'Кросс-сейл существующему клиенту', 5),
(14, 'call', '2024-06-02 16:00:00', 'Квалификация', 15),
(15, 'meeting', '2024-06-10 11:00:00', 'Демо новой фичи', 60),
(16, 'call', '2024-06-20 15:00:00', 'Обсуждение скидки', 25),
(17, 'email', '2024-06-30 10:00:00', 'КП отправлено', 5),
(17, 'call', '2024-07-01 13:00:00', 'Согласован договор', 20),
(18, 'call', '2024-07-09 11:45:00', 'Возврат клиента', 30),
(19, 'email', '2024-07-19 14:00:00', 'Клиент ушёл к конкуренту', 5),
(20, 'call', '2024-07-31 10:30:00', 'Новый лид из формы', 15),
(21, 'meeting', '2024-08-08 14:00:00', 'Презентация для руководства', 90),
(21, 'call', '2024-08-09 11:00:00', 'Согласование', 25),
(22, 'email', '2024-08-19 10:00:00', 'Допродажа', 5),
(22, 'call', '2024-08-20 16:00:00', 'Обсуждение условий', 20),
(23, 'call', '2024-08-31 11:00:00', 'Закрытие сделки', 30),
(24, 'email', '2024-09-10 09:00:00', 'Презентация отправлена', 5),
(25, 'call', '2024-09-20 14:00:00', 'Клиент не готов', 15),
(26, 'meeting', '2024-09-30 15:00:00', 'Большая презентация', 100),
(26, 'call', '2024-10-01 11:00:00', 'Согласование цены', 25),
(27, 'email', '2024-10-10 10:00:00', 'КП', 5),
(27, 'call', '2024-10-11 14:00:00', 'Переговоры', 30),
(28, 'meeting', '2024-10-20 16:00:00', 'Финал, подписание', 60),
(29, 'call', '2024-10-31 09:00:00', 'Новый лид', 20),
(30, 'call', '2024-11-11 13:00:00', 'Крупная сделка, VIP', 40);

CREATE INDEX idx_deals_manager ON deals(manager_id);
CREATE INDEX idx_deals_email ON deals(client_email);
CREATE INDEX idx_deals_stage ON deals(stage);
CREATE INDEX idx_interactions_deal ON interactions(deal_id);
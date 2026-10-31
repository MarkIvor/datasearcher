"""Генератор демо SQLite-БД для локального запуска без Docker.

Создаёт:
  backend/demo_data/sales.db      — 50 клиентов, 20 товаров, 300 заказов (FK-связи)
  backend/demo_data/marketing.db  — 30 строк маркетинговой аналитики

Запуск (из корня репозитория):
    python demo-data/make_demo_dbs.py

Затем в UI: Setup-визард (шаг «Данные») или вкладка «БД» →
тип SQLite, путь к файлу — абсолютный путь к sales.db / marketing.db.
"""
from __future__ import annotations

import os
import random
import sqlite3
from datetime import date, timedelta

random.seed(42)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "backend", "demo_data"))

FIRST_NAMES = ["Анна", "Борис", "Вика", "Гога", "Дима", "Елена", "Жанна", "Захар",
               "Ирина", "Кирилл", "Лена", "Максим", "Наташа", "Олег", "Полина",
               "Роман", "Света", "Тимур", "Ульяна", "Фёдор"]
LAST_NAMES = ["Иванов", "Петров", "Сидоров", "Кузнецов", "Смирнов", "Волков",
              "Морозов", "Новиков", "Орлов", "Егоров"]
CITIES = ["Москва", "Санкт-Петербург", "Казань", "Новосибирск", "Екатеринбург"]
SEGMENTS = ["VIP", "Стандарт", "Новый"]

PRODUCTS = [
    ("Ноутбук Pro 15", "Электроника"), ("Смартфон X20", "Электроника"),
    ("Наушники AirSound", "Электроника"), ("Планшет Tab 11", "Электроника"),
    ("Умные часы Fit", "Электроника"), ("Футболка хлопок", "Одежда"),
    ("Джинсы Slim", "Одежда"), ("Куртка зимняя", "Одежда"),
    ("Кроссовки Run", "Одежда"), ("Платье летнее", "Одежда"),
    ("Роман «Данные и смысл»", "Книги"), ("Справочник SQL", "Книги"),
    ("Книга о ML", "Книги"), ("Комикс «Бенто»", "Книги"),
    ("Настольная лампа", "Дом"), ("Кофеварка 2в1", "Дом"),
    ("Набор кастрюль", "Дом"), ("Плед шерстяной", "Дом"),
    ("Гантели 2×5кг", "Спорт"), ("Коврик для йоги", "Спорт"),
]
STATUSES = ["completed", "completed", "completed", "completed", "pending", "cancelled"]


def make_sales_db(path: str) -> None:
    con = sqlite3.connect(path)
    cur = con.cursor()

    cur.execute("DROP TABLE IF EXISTS orders")
    cur.execute("DROP TABLE IF EXISTS products")
    cur.execute("DROP TABLE IF EXISTS customers")

    cur.execute("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            age INTEGER,
            balance REAL,
            segment TEXT,
            registered_date TEXT
        )
    """)
    customers = []
    for i in range(1, 51):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        customers.append((
            i, name, random.choice(CITIES),
            random.randint(19, 65),
            round(random.uniform(500, 120000), 2),
            random.choice(SEGMENTS),
            (date(2024, 1, 1) + timedelta(days=random.randint(0, 400))).isoformat(),
        ))
    cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?)", customers)

    cur.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL,
            stock INTEGER
        )
    """)
    products = []
    for i, (name, cat) in enumerate(PRODUCTS, start=1):
        products.append((i, name, cat, round(random.uniform(300, 95000), 2), random.randint(0, 140)))
    cur.executemany("INSERT INTO products VALUES (?,?,?,?,?)", products)

    cur.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER REFERENCES customers(id),
            product_id INTEGER REFERENCES products(id),
            quantity INTEGER,
            amount REAL,
            status TEXT,
            order_date TEXT
        )
    """)
    orders = []
    for i in range(1, 301):
        cid = random.randint(1, 50)
        pid = random.randint(1, len(PRODUCTS))
        qty = random.randint(1, 4)
        price = products[pid - 1][3]
        orders.append((
            i, cid, pid, qty,
            round(qty * price * random.uniform(0.85, 1.15), 2),
            random.choice(STATUSES),
            (date(2025, 1, 1) + timedelta(days=random.randint(0, 600))).isoformat(),
        ))
    cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", orders)

    con.commit()
    con.close()
    print(f"OK {path}: 50 customers, {len(PRODUCTS)} products, 300 orders")


def make_marketing_db(path: str) -> None:
    src = os.path.join(HERE, "marketing_metrics.csv")
    rows = []
    with open(src, encoding="utf-8") as f:
        header = f.readline().strip().split(",")
        for line in f:
            rows.append(line.strip().split(","))

    con = sqlite3.connect(path)
    cur = con.cursor()
    cols = ", ".join(f'"{c}" TEXT' for c in header)
    cur.execute(f"CREATE TABLE marketing_metrics ({cols})")
    ph = ", ".join("?" for _ in header)
    cur.executemany(f"INSERT INTO marketing_metrics VALUES ({ph})", rows)
    con.commit()
    con.close()
    print(f"OK {path}: {len(rows)} rows marketing_metrics")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    make_sales_db(os.path.join(OUT_DIR, "sales.db"))
    make_marketing_db(os.path.join(OUT_DIR, "marketing.db"))
    print(f"Готово. Демо-БД в: {OUT_DIR}")


if __name__ == "__main__":
    main()

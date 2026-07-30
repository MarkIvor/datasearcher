"""Авто-создание демо-подключений при старте.

Создаёт 3 подключения (PostgreSQL e-commerce, MySQL CRM, ClickHouse analytics)
в БД приложения, если их ещё нет. Пользователь увидит их сразу в UI
во вкладке «БД» — без ручного ввода параметров.
"""
from __future__ import annotations

import logging

from .auth_service import encrypt_connection_string
from ..models.database import DBConnection, SessionLocal

logger = logging.getLogger("datasearcher.seed")

DEMO_CONNECTIONS = [
    {
        "name": "PostgreSQL · e-commerce",
        "db_type": "postgresql",
        "conn_str": "postgresql+psycopg2://datasearcher:ds_demo_pass_2024@postgres:5432/ecommerce",
        "is_public": True,
    },
    {
        "name": "MySQL · CRM",
        "db_type": "mysql",
        "conn_str": "mysql+pymysql://datasearcher:ds_demo_pass_2024@mysql:3306/crm?charset=utf8mb4",
        "is_public": True,
    },
    {
        "name": "ClickHouse · web analytics",
        "db_type": "clickhouse",
        "conn_str": '{"host":"clickhouse","port":8123,"username":"datasearcher","password":"ds_demo_pass_2024","database":"default"}',
        "is_public": True,
    },
]


def seed_demo_connections() -> None:
    """Создать демо-подключения, если их ещё нет в БД приложения."""
    from ..models.database import User

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            logger.info("seed: нет админа — пропускаю")
            return

        created = 0
        for cfg in DEMO_CONNECTIONS:
            existing = db.query(DBConnection).filter(
                DBConnection.name == cfg["name"],
                DBConnection.db_type == cfg["db_type"],
            ).first()
            if existing:
                continue

            conn = DBConnection(
                user_id=admin.id,
                name=cfg["name"],
                db_type=cfg["db_type"],
                connection_string=encrypt_connection_string(cfg["conn_str"]),
                is_public=cfg["is_public"],
            )
            db.add(conn)
            created += 1

        if created:
            db.commit()
            logger.info("seed: создано %d демо-подключений", created)
    except Exception as e:
        logger.warning("seed: ошибка: %s", e)
        db.rollback()
    finally:
        db.close()
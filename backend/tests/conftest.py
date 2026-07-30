from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Подменяем env-переменные ДО импорта app, чтобы тесты были изолированы.
_TMP = tempfile.mkdtemp(prefix="ds_test_")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-fixed-for-tests-1234567890")
os.environ.setdefault("ENCRYPTION_KEY", "")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("ADMIN_PASSWORD", "testpass123")
os.environ.setdefault("UPLOAD_DIR", os.path.join(_TMP, "uploads"))
os.environ.setdefault("KB_DB_PATH", os.path.join(_TMP, "test_kb.db"))
os.environ.setdefault("LOG_DB_PATH", os.path.join(_TMP, "test_logs.db"))
os.environ.setdefault("EMBEDDINGS_DIR", os.path.join(_TMP, "embeddings"))
os.environ.setdefault("LOG_ENABLED", "true")
os.environ.setdefault("PII_MASKING", "true")
os.environ.setdefault("READ_ONLY", "true")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

from app.models.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.services import knowledge_base as kb_mod  # noqa: E402
from app.services import logging_db as log_mod  # noqa: E402
from app.services import example_store as ex_mod  # noqa: E402


@pytest.fixture(scope="session")
def tmp_dir():
    return _TMP


@pytest.fixture(scope="session", autouse=True)
def _init_db_once():
    """Создать таблицы SQLAlchemy один раз для сессии тестов."""
    init_db()
    yield
    # не закрываем engine — pytest сам почистит процесс


@pytest.fixture()
def db():
    """Свежая SQLAlchemy-сессия (откатывается после каждого теста)."""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def _reset_kb_singletons():
    """Сбросить синглтоны KB/Logs/ExampleStore между тестами,
    чтобы каждый тест получил чистую SQLite-БД по пути из env."""
    # Закрыть соединения синглтонов (если держат SQLite-курсоры)
    kb_mod._kb = None
    log_mod._log_db = None
    ex_mod._example_store = None
    import gc
    gc.collect()
    # Удаляем файлы SQLite для чистого старта каждого теста
    for p in (
        os.environ["KB_DB_PATH"],
        os.environ["LOG_DB_PATH"],
        os.path.join(os.path.dirname(os.environ["KB_DB_PATH"]), "datasearcher_examples.db"),
    ):
        for _ in range(3):
            try:
                os.remove(p)
                break
            except (FileNotFoundError, PermissionError):
                try:
                    # переименуем, чтобы не блокировать тесты
                    os.rename(p, p + ".bak")
                except (FileNotFoundError, PermissionError):
                    pass
                break
    yield


@pytest.fixture()
def kb():
    from app.services.knowledge_base import get_kb
    return get_kb()


@pytest.fixture()
def log_db():
    from app.services.logging_db import get_log_db
    return get_log_db()


@pytest.fixture()
def duckdb_session():
    """In-memory DuckDB-сессия для тестирования инструментов."""
    import duckdb
    from app.session import Session, FileInfo  # noqa: F401

    conn = duckdb.connect()
    conn.execute("SET memory_limit='1GB'")
    session = Session(id="test_sess_001", conn=conn)
    yield session
    try:
        conn.close()
    except Exception:
        pass


@pytest.fixture()
def sample_csv(tmp_path) -> str:
    """CSV-файл с тестовыми данными для инструментов."""
    p = tmp_path / "sample.csv"
    p.write_text(
        "id,name,email,amount,order_date,region\n"
        "1,Анна,anna@example.com,1500.50,2024-01-15,Москва\n"
        "2,Борис,boris@mail.com,2300.00,2024-02-20,СПб\n"
        "3,Анна,anna@example.com,1500.50,2024-01-15,Москва\n"
        "4,Вика,vika@company.org,99999.99,2024-03-10,Москва\n"
        "5,Гога,goga@gmail.com,800.25,2024-04-05,Казань\n"
        "6,Дима,,500.00,2024-05-12,СПб\n"
        "7,Елена,elena@test.ru,1200.00,,Новосибирск\n",
        encoding="utf-8",
    )
    return str(p)


@pytest.fixture()
def loaded_session(duckdb_session, sample_csv):
    """DuckDB-сессия с загруженной sample-таблицей через engine."""
    from app.services.engine import get_engine_for_session
    eng = get_engine_for_session(duckdb_session)
    fi = eng.load_csv(sample_csv, table_name="sample")
    assert fi is not None, "CSV должен загрузиться"
    return duckdb_session, eng, fi


@pytest.fixture()
def client():
    """FastAPI TestClient с переопределённой DB (in-memory SQLite)."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.models.database import get_db

    # Изолированная SQLite-БД для API-тестов
    test_db_path = os.path.join(_TMP, "test_api.db")
    try:
        os.remove(test_db_path)
    except FileNotFoundError:
        pass

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    api_engine = create_engine(f"sqlite:///{test_db_path}", connect_args={"check_same_thread": False})
    ApiSessionLocal = sessionmaker(bind=api_engine)
    Base.metadata.create_all(api_engine)

    def override_get_db():
        s = ApiSessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    # Сеем админа
    from app.services.auth_service import hash_password
    from app.models.database import User, AppSettings
    s = ApiSessionLocal()
    try:
        if not s.query(User).filter(User.email == "admin@test.local").first():
            s.add(User(
                email="admin@test.local",
                password_hash=hash_password("testpass123"),
                display_name="Test Admin",
                role="admin",
                is_active=True,
            ))
            s.commit()
        # Базовые настройки
        for k, v in [
            ("allow_registration", "true"),
            ("allow_custom_llm", "true"),
            ("allow_user_db_connections", "true"),
        ]:
            if not s.query(AppSettings).filter(AppSettings.key == k).first():
                s.add(AppSettings(key=k, value=v))
        s.commit()
    finally:
        s.close()

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    try:
        api_engine.dispose()
    except Exception:
        pass
    try:
        os.remove(test_db_path)
    except (FileNotFoundError, PermissionError):
        pass


@pytest.fixture()
def authed_client(client):
    """TestClient с залогиненным админом (cookie access_token)."""
    from app.services.auth_service import create_access_token
    from app.models.database import SessionLocal, User

    # Найти админ-user_id
    s = SessionLocal()
    try:
        user = s.query(User).filter(User.email == "admin@test.local").first()
        uid = user.id if user else 1
    finally:
        s.close()

    token = create_access_token(uid, "admin")
    client.cookies.set("access_token", token)
    return client
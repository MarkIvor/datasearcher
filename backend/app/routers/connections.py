from __future__ import annotations

import json
import os
import re
import tempfile

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models.database import get_db, User, DBConnection
from ..services.auth_service import (
    get_app_setting, encrypt_connection_string, decrypt_connection_string,
)
from .auth import get_current_user

router = APIRouter(prefix="/api/connections", tags=["connections"])


class CreateConnectionRequest(BaseModel):
    name: str
    db_type: str
    host: str = ""
    port: int = 0
    database: str = ""
    username: str = ""
    password: str = ""
    is_public: bool = False


class UpdateConnectionRequest(BaseModel):
    name: str | None = None
    is_public: bool | None = None


def _build_conn_str(body: CreateConnectionRequest) -> str:
    if body.db_type == "sqlite":
        return f"sqlite:///{body.database}"
    elif body.db_type == "clickhouse":
        return json.dumps({
            "host": body.host, "port": body.port or 8123,
            "username": body.username, "password": body.password,
            "database": body.database,
        })
    elif body.db_type == "mysql":
        return f"mysql+pymysql://{body.username}:{body.password}@{body.host}:{body.port or 3306}/{body.database}"
    else:
        return f"postgresql+psycopg2://{body.username}:{body.password}@{body.host}:{body.port or 5432}/{body.database}"


def _parse_clickhouse_params(conn_str: str) -> dict:
    try:
        return json.loads(conn_str)
    except Exception:
        m = re.match(r"clickhouse://([^:]*):([^@]*)@([^:]*):(\d+)/(.*)", conn_str)
        if m:
            return {"username": m.group(1), "password": m.group(2), "host": m.group(3), "port": int(m.group(4)), "database": m.group(5)}
        return {"host": "localhost", "port": 8123, "username": "", "password": "", "database": ""}


def _set_session_cookie(response, session_id: str):
    response.set_cookie("session_id", session_id, max_age=86400, httponly=False)


def _load_table_sqlalchemy(session, conn_id: str, conn_str: str, list_tables_fn, quote_fn=None) -> tuple[int, list[str]]:
    if quote_fn is None:
        quote_fn = lambda t: f'"{t}"'
    from sqlalchemy import create_engine, text
    eng = create_engine(conn_str, pool_pre_ping=True)
    tables_added = 0
    errors = []
    with eng.connect() as c:
        table_names = list_tables_fn(c)
    for tbl in table_names[:30]:
        safe_tbl = tbl.replace('"', '""')
        q = quote_fn(tbl)
        try:
            with eng.connect() as c:
                sample = c.execute(text(f'SELECT * FROM {q} LIMIT 1')).fetchall()
                cols = list(sample[0]._mapping.keys()) if sample else []
                count_row = c.execute(text(f'SELECT COUNT(*) FROM {q}')).fetchone()
                row_count = count_row[0] if count_row else 0
                col_info = [{"name": col, "type": "unknown"} for col in cols]
                chunk = c.execute(text(f'SELECT * FROM {q} LIMIT 50000')).fetchall()
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8")
            import csv
            writer = csv.writer(tmp)
            writer.writerow(cols)
            for row in chunk:
                writer.writerow([str(v) if v is not None else "" for v in row])
            tmp.close()
            try:
                for _ in range(2):
                    try:
                        session.conn.execute(f'DROP TABLE IF EXISTS "{safe_tbl}"')
                    except Exception:
                        pass
                    try:
                        session.conn.execute(f'DROP VIEW IF EXISTS "{safe_tbl}"')
                    except Exception:
                        pass
                session.conn.execute(f'CREATE TABLE "{safe_tbl}" AS SELECT * FROM read_csv_auto(\'{tmp.name}\', header=true, all_varchar=false)')
                desc_result = session.conn.execute(f'DESCRIBE "{safe_tbl}"').fetchall()
                col_info = [{"name": r[0], "type": r[1]} for r in desc_result]
            finally:
                try:
                    os.unlink(tmp.name)
                except Exception:
                    pass
            from ..session import FileInfo
            fi = FileInfo(
                id=f"db_{conn_id}_{tbl}",
                name=tbl,
                table_name=safe_tbl,
                file_type="db_view",
                csv_path="",
                row_count=row_count,
                columns=col_info,
            )
            session.files[fi.id] = fi
            tables_added += 1
        except Exception as ex:
            errors.append(f"{tbl}: {ex}")
    return tables_added, errors


def _pg_list_tables(c):
    rows = c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).fetchall()
    return [r[0] for r in rows]


def _mysql_list_tables(c):
    rows = c.execute(text("SHOW TABLES")).fetchall()
    return [r[0] for r in rows]

def _mysql_quote(tbl):
    return f"`{tbl}`"


@router.get("/")
async def list_connections(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conns = db.query(DBConnection).filter(
        (DBConnection.user_id == user.id) | (DBConnection.is_public == True)
    ).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "db_type": c.db_type,
            "is_public": c.is_public,
            "is_owner": c.user_id == user.id,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in conns
    ]


@router.post("/")
async def create_connection(body: CreateConnectionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    allow = get_app_setting(db, "allow_user_db_connections")
    if allow != "true" and user.role != "admin":
        raise HTTPException(403, "Создание подключений отключено администратором")

    if body.db_type not in ("postgresql", "mysql", "clickhouse", "sqlite"):
        raise HTTPException(400, f"Неподдерживаемый тип БД: {body.db_type}")

    conn_str = _build_conn_str(body)
    encrypted = encrypt_connection_string(conn_str)

    existing = db.query(DBConnection).filter(
        DBConnection.user_id == user.id,
        DBConnection.db_type == body.db_type,
        DBConnection.name == body.name,
    ).first()
    if existing:
        existing.connection_string = encrypted
        existing.is_public = body.is_public
        db.commit()
        db.refresh(existing)
        return {"id": existing.id, "name": existing.name, "db_type": existing.db_type}

    conn = DBConnection(
        user_id=user.id,
        name=body.name,
        db_type=body.db_type,
        connection_string=encrypted,
        is_public=body.is_public,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return {"id": conn.id, "name": conn.name, "db_type": conn.db_type}


@router.post("/{conn_id}/test")
async def test_connection(conn_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conn = db.query(DBConnection).filter(DBConnection.id == conn_id).first()
    if not conn or (conn.user_id != user.id and not conn.is_public):
        raise HTTPException(404, "Подключение не найдено")

    conn_str = decrypt_connection_string(conn.connection_string)
    try:
        if conn.db_type == "clickhouse":
            import clickhouse_connect
            params = _parse_clickhouse_params(conn_str)
            client = clickhouse_connect.get_client(
                host=params["host"], port=params["port"],
                username=params["username"], password=params["password"],
                database=params["database"],
            )
            client.command("SELECT 1")
        elif conn.db_type == "sqlite":
            db_path = conn_str.replace("sqlite:///", "")
            from sqlalchemy import create_engine, text
            eng = create_engine(f"sqlite:///{db_path}")
            with eng.connect() as c:
                c.execute(text("SELECT 1"))
        else:
            from sqlalchemy import create_engine, text
            eng = create_engine(conn_str, pool_pre_ping=True)
            with eng.connect() as c:
                c.execute(text("SELECT 1"))
        return {"ok": True, "message": "Подключение успешно"}
    except Exception as e:
        return {"ok": False, "message": f"Ошибка: {e}"}


@router.post("/{conn_id}/attach")
async def attach_connection(conn_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conn = db.query(DBConnection).filter(DBConnection.id == conn_id).first()
    if not conn or (conn.user_id != user.id and not conn.is_public):
        raise HTTPException(404, "Подключение не найдено")

    conn_str = decrypt_connection_string(conn.connection_string)
    mgr = request.app.state.session_manager
    session_id = request.cookies.get("session_id")
    session = mgr.get_or_create(session_id)

    tables_added = 0
    errors = []

    try:
        if conn.db_type == "postgresql":
            tables_added, errors = _load_table_sqlalchemy(session, str(conn_id), conn_str, _pg_list_tables)

        elif conn.db_type == "mysql":
            tables_added, errors = _load_table_sqlalchemy(session, str(conn_id), conn_str, _mysql_list_tables, _mysql_quote)

        elif conn.db_type == "sqlite":
            db_path = conn_str.replace("sqlite:///", "")
            if not os.path.isfile(db_path):
                return JSONResponse(content={"ok": False, "message": f"Файл не найден: {db_path}"})
            tables_added, errors = _load_table_sqlalchemy(
                session, str(conn_id),
                f"sqlite:///{db_path}",
                lambda c: [r[0] for r in c.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()],
            )

        elif conn.db_type == "clickhouse":
            import clickhouse_connect
            params = _parse_clickhouse_params(conn_str)
            client = clickhouse_connect.get_client(
                host=params["host"], port=params["port"],
                username=params["username"], password=params["password"],
                database=params["database"],
            )
            tables_result = client.command("SHOW TABLES")
            if isinstance(tables_result, str):
                table_names = [t.strip() for t in tables_result.strip().split("\n") if t.strip()]
            elif hasattr(tables_result, "result_rows"):
                table_names = [r[0] for r in tables_result.result_rows]
            else:
                table_names = list(tables_result) if tables_result else []

            errors = []
            for tbl in table_names[:30]:
                safe_tbl = tbl.replace('"', '""')
                try:
                    data = client.query_dataframe(f"SELECT * FROM `{tbl}` LIMIT 50000")
                    count_row = client.command(f"SELECT COUNT(*) FROM `{tbl}`")
                    row_count = int(count_row) if count_row else len(data)
                    if len(data) == 0:
                        continue
                    col_info = []
                    for col in data.columns:
                        dtype = str(data[col].dtype)
                        if "int" in dtype:
                            ctype = "integer"
                        elif "float" in dtype:
                            ctype = "double"
                        else:
                            ctype = "varchar"
                        col_info.append({"name": col, "type": ctype})
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
                    data.to_csv(tmp.name, index=False)
                    tmp.close()
                    try:
                        for _ in range(2):
                            try:
                                session.conn.execute(f'DROP TABLE IF EXISTS "{safe_tbl}"')
                            except Exception:
                                pass
                            try:
                                session.conn.execute(f'DROP VIEW IF EXISTS "{safe_tbl}"')
                            except Exception:
                                pass
                        session.conn.execute(f'CREATE TABLE "{safe_tbl}" AS SELECT * FROM read_csv_auto(\'{tmp.name}\', header=true, all_varchar=false)')
                        desc_result = session.conn.execute(f'DESCRIBE "{safe_tbl}"').fetchall()
                        col_info = [{"name": r[0], "type": r[1]} for r in desc_result]
                    finally:
                        try:
                            os.unlink(tmp.name)
                        except Exception:
                            pass
                    from ..session import FileInfo
                    fi = FileInfo(
                        id=f"db_{conn_id}_{tbl}",
                        name=tbl,
                        table_name=safe_tbl,
                        file_type="db_view",
                        csv_path="",
                        row_count=row_count,
                        columns=col_info,
                    )
                    session.files[fi.id] = fi
                    tables_added += 1
                except Exception as ex:
                    errors.append(f"{tbl}: {ex}")

        if tables_added == 0:
            msg = "Не удалось загрузить ни одну таблицу"
            if errors:
                msg += f". Первая ошибка: {errors[0]}"
            resp = JSONResponse(content={"ok": False, "message": msg})
        else:
            files_list = [
                {
                    "file_id": fi.id,
                    "table_name": fi.table_name,
                    "file_type": fi.file_type,
                    "row_count": fi.row_count,
                    "columns": fi.columns,
                }
                for fi in session.files.values()
            ]
            resp = JSONResponse(content={"ok": True, "tables_loaded": tables_added, "files": files_list})
    except Exception as e:
        resp = JSONResponse(content={"ok": False, "message": f"Ошибка подключения: {e}"})

    _set_session_cookie(resp, session.id)
    return resp


@router.put("/{conn_id}")
async def update_connection(conn_id: int, body: UpdateConnectionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conn = db.query(DBConnection).filter(DBConnection.id == conn_id).first()
    if not conn or (conn.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Подключение не найдено")

    if body.name is not None:
        conn.name = body.name
    if body.is_public is not None:
        conn.is_public = body.is_public
    db.commit()
    return {"ok": True}


@router.delete("/{conn_id}")
async def delete_connection(conn_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conn = db.query(DBConnection).filter(DBConnection.id == conn_id).first()
    if not conn or (conn.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Подключение не найдено")
    db.delete(conn)
    db.commit()
    return {"ok": True}

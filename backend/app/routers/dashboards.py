from __future__ import annotations

import csv
import json
import os
import secrets
import tempfile

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..models.database import get_db, User, Dashboard
from ..services.auth_service import hash_password, verify_password
from .auth import get_current_user

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])

DASHBOARDS_DIR = os.path.join(tempfile.gettempdir(), "datasearcher_dashboards")
os.makedirs(DASHBOARDS_DIR, exist_ok=True)


class GenerateDashboardRequest(BaseModel):
    title: str = ""
    description: str = ""
    password: str = ""


class DashboardAuthRequest(BaseModel):
    password: str


class DashboardQueryRequest(BaseModel):
    filters: dict = {}


def _generate_slug() -> str:
    return secrets.token_urlsafe(6)[:8]


def _create_snapshot(session) -> tuple[str, list[dict]]:
    slug = _generate_slug()
    snap_dir = os.path.join(DASHBOARDS_DIR, slug)
    os.makedirs(snap_dir, exist_ok=True)

    tables_info = []
    for fi in session.files.values():
        csv_path = os.path.join(snap_dir, f"{fi.table_name}.csv")
        try:
            result = session.conn.execute(f'SELECT * FROM "{fi.table_name}"')
            columns = [d[0] for d in result.description]
            rows = result.fetchall()
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow([str(v) if v is not None else "" for v in row])

            desc = session.conn.execute(f'DESCRIBE "{fi.table_name}"').fetchall()
            actual_types = {r[0]: r[1] for r in desc}

            enriched_columns = []
            for col in fi.columns:
                enriched_columns.append({
                    "name": col["name"],
                    "type": actual_types.get(col["name"], col.get("type", "unknown")),
                })

            tables_info.append({
                "name": fi.table_name,
                "row_count": len(rows),
                "columns": enriched_columns,
            })
        except Exception:
            pass

    return snap_dir, tables_info


@router.post("/generate")
async def generate_dashboard(body: GenerateDashboardRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mgr = request.app.state.session_manager
    session_id = request.cookies.get("session_id")
    session = mgr.get_or_create(session_id)

    if not session.files:
        raise HTTPException(400, "Нет загруженных данных для дашборда")

    snap_dir, tables_info = _create_snapshot(session)

    table_descriptions = []
    for t in tables_info:
        cols_desc = ", ".join(f"{c['name']}({c.get('type','?')})" for c in t["columns"])
        table_descriptions.append(f"Таблица \"{t['name']}\" ({t['row_count']} строк): {cols_desc}")

    tables_text = "\n".join(table_descriptions)

    from ..services.llm_service import LLMService
    llm = LLMService.from_user_settings(db, user.id)

    prompt = f"""Ты — аналитик данных. На основе описания таблиц создай конфигурацию публичного дашборда.

Доступные таблицы:
{tables_text}

Создай JSON-конфигурацию дашборда со следующей структурой:
{{
  "title": "Название дашборда",
  "description": "Краткое описание",
  "selectors": [
    {{"id": "slug", "type": "category|date_range|number_range", "column": "имя_колонки", "table": "имя_таблицы", "label": "Метка"}}
  ],
  "cards": [
    {{"id": "slug", "type": "kpi|chart|table", "title": "Заголовок",
      "query": "SQL запрос с использованием {{WHERE}} как плейсхолдера для фильтров. Имена таблиц в кавычках.",
      "chart_type": "line|bar|pie|area|scatter",
      "x": "колонка для оси X (для chart)",
      "y": "колонка для оси Y (для chart)",
      "format": "number|currency|percent",
      "prefix": "",
      "suffix": ""}}
  ]
}}

ПРАВИЛА:
1. Создай 3-5 селекторов по самым полезным колонкам (категории, даты, числа)
2. Создай 2-3 KPI-карточки с агрегатами (SUM, COUNT, AVG)
3. Создай 3-5 графиков (разные типы: line для трендов, bar для сравнений, pie для долей, scatter для корреляций)
4. В каждом SQL-запросе используй {{WHERE}} как плейсхолдер — туда будут подставлены фильтры из селекторов
5. Все имена таблиц и колонок бери в двойные кавычки
6. Дашборд должен быть максимально информативным и красивым
7. Ответь ТОЛЬКО валидным JSON, без markdown-обёрток

JSON:"""

    try:
        result = await llm._single_completion([
            {"role": "system", "content": "Ты генератор конфигураций дашбордов. Отвечай ТОЛЬКО валидным JSON."},
            {"role": "user", "content": prompt},
        ])
    except Exception as e:
        raise HTTPException(500, f"Ошибка генерации: {e}")

    result = result.strip()
    if result.startswith("```"):
        result = result.split("\n", 1)[1] if "\n" in result else result[3:]
        result = result.rsplit("```", 1)[0]
    result = result.strip()

    try:
        config = json.loads(result)
    except json.JSONDecodeError:
        raise HTTPException(500, f"LLM вернула невалидный JSON: {result[:200]}")

    slug = _generate_slug()
    while db.query(Dashboard).filter(Dashboard.slug == slug).first():
        slug = _generate_slug()

    dash_title = body.title or config.get("title", "Dashboard")
    dash_desc = body.description or config.get("description", "")

    dash = Dashboard(
        slug=slug,
        title=dash_title,
        description=dash_desc,
        password_hash=hash_password(body.password) if body.password else None,
        config=config,
        snapshot_dir=snap_dir,
        tables_info=tables_info,
        created_by=user.id,
    )
    db.add(dash)
    db.commit()
    db.refresh(dash)

    api_base = str(request.base_url).rstrip("/")
    return {
        "id": dash.id,
        "slug": slug,
        "title": dash_title,
        "description": dash_desc,
        "url": f"{api_base}/d/{slug}",
        "has_password": bool(dash.password_hash),
        "created_at": dash.created_at.isoformat() if dash.created_at else None,
    }


@router.get("/")
async def list_dashboards(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dashes = db.query(Dashboard).filter(Dashboard.created_by == user.id, Dashboard.is_active == True).order_by(Dashboard.id.desc()).all()
    return [
        {
            "id": d.id,
            "slug": d.slug,
            "title": d.title,
            "description": d.description,
            "has_password": bool(d.password_hash),
            "views": d.views,
            "tables_count": len(d.tables_info or []),
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in dashes
    ]


@router.get("/{slug}")
async def get_dashboard(slug: str, db: Session = Depends(get_db)):
    dash = db.query(Dashboard).filter(Dashboard.slug == slug, Dashboard.is_active == True).first()
    if not dash:
        raise HTTPException(404, "Дашборд не найден")

    dash.views += 1
    db.commit()

    return {
        "slug": dash.slug,
        "title": dash.title,
        "description": dash.description,
        "has_password": bool(dash.password_hash),
        "config": dash.config,
        "tables_info": dash.tables_info,
        "views": dash.views,
        "created_at": dash.created_at.isoformat() if dash.created_at else None,
    }


@router.post("/{slug}/auth")
async def auth_dashboard(slug: str, body: DashboardAuthRequest, db: Session = Depends(get_db)):
    dash = db.query(Dashboard).filter(Dashboard.slug == slug, Dashboard.is_active == True).first()
    if not dash:
        raise HTTPException(404, "Дашборд не найден")

    if not dash.password_hash:
        return {"token": slug}

    if not verify_password(body.password, dash.password_hash):
        raise HTTPException(403, "Неверный пароль")

    import hashlib
    token = hashlib.sha256(f"{slug}:{body.password}".encode()).hexdigest()[:16]
    return {"token": token}


@router.get("/{slug}/options")
async def get_selector_options(slug: str, table: str, column: str, db: Session = Depends(get_db)):
    dash = db.query(Dashboard).filter(Dashboard.slug == slug, Dashboard.is_active == True).first()
    if not dash:
        raise HTTPException(404, "Дашборд не найден")

    import duckdb
    conn = duckdb.connect()
    try:
        conn.execute("SET memory_limit='500MB'")
        for t in (dash.tables_info or []):
            csv_path = os.path.join(dash.snapshot_dir, f"{t['name']}.csv")
            if os.path.isfile(csv_path):
                conn.execute(f'CREATE TABLE IF NOT EXISTS "{t["name"]}" AS SELECT * FROM read_csv_auto(\'{csv_path}\', header=true, all_varchar=false)')

        try:
            result = conn.execute(f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL ORDER BY "{column}" LIMIT 100').fetchall()
            values = [str(r[0]) for r in result]
            return {"values": values}
        except Exception as e:
            return {"values": [], "error": str(e)}
    finally:
        conn.close()


@router.post("/{slug}/query")
async def query_dashboard(slug: str, body: DashboardQueryRequest, request: Request, db: Session = Depends(get_db)):
    dash = db.query(Dashboard).filter(Dashboard.slug == slug, Dashboard.is_active == True).first()
    if not dash:
        raise HTTPException(404, "Дашборд не найден")

    if dash.password_hash:
        token = request.headers.get("x-dash-token", "")
        if not token:
            raise HTTPException(403, "Требуется пароль")

    import duckdb
    conn = duckdb.connect()
    try:
        conn.execute("SET memory_limit='1GB'")

        for t in (dash.tables_info or []):
            csv_path = os.path.join(dash.snapshot_dir, f"{t['name']}.csv")
            if os.path.isfile(csv_path):
                conn.execute(f'CREATE TABLE IF NOT EXISTS "{t["name"]}" AS SELECT * FROM read_csv_auto(\'{csv_path}\', header=true, all_varchar=false)')

        where_clauses = []
        filters = body.filters
        selectors = (dash.config or {}).get("selectors", [])

        for sel in selectors:
            sid = sel.get("id", "")
            col = sel.get("column", "")
            tbl = sel.get("table", "")
            stype = sel.get("type", "")
            val = filters.get(sid)

            if val is None or val == "" or val == []:
                continue

            qualified = f'"{tbl}"."{col}"' if tbl else f'"{col}"'

            if stype == "category":
                if isinstance(val, list):
                    vals = ", ".join(f"'{v}'" for v in val)
                    where_clauses.append(f"{qualified} IN ({vals})")
                else:
                    where_clauses.append(f"{qualified} = '{val}'")
            elif stype == "date_range":
                if isinstance(val, dict):
                    if val.get("from"):
                        where_clauses.append(f"{qualified} >= '{val['from']}'")
                    if val.get("to"):
                        where_clauses.append(f"{qualified} <= '{val['to']}'")
            elif stype == "number_range":
                if isinstance(val, dict):
                    if val.get("min") is not None:
                        where_clauses.append(f"{qualified} >= {val['min']}")
                    if val.get("max") is not None:
                        where_clauses.append(f"{qualified} <= {val['max']}")

        import re

        def tables_in_query(sql: str) -> set[str]:
            pattern = r'(?:FROM|JOIN)\s+"([^"]+)"'
            return set(re.findall(pattern, sql, re.IGNORECASE))

        cards = (dash.config or {}).get("cards", [])
        results = []

        for card in cards:
            query = card.get("query", "")
            if not query:
                continue

            query_tables = tables_in_query(query)

            card_where = []
            for sel in selectors:
                sid = sel.get("id", "")
                col = sel.get("column", "")
                tbl = sel.get("table", "")
                stype = sel.get("type", "")
                val = filters.get(sid)

                if val is None or val == "" or val == []:
                    continue

                if tbl and tbl not in query_tables:
                    continue

                qualified = f'"{tbl}"."{col}"' if tbl else f'"{col}"'

                if stype == "category":
                    if isinstance(val, list):
                        vals = ", ".join(f"'{v}'" for v in val)
                        card_where.append(f"{qualified} IN ({vals})")
                    else:
                        card_where.append(f"{qualified} = '{val}'")
                elif stype == "date_range":
                    if isinstance(val, dict):
                        if val.get("from"):
                            card_where.append(f"{qualified} >= '{val['from']}'")
                        if val.get("to"):
                            card_where.append(f"{qualified} <= '{val['to']}'")
                elif stype == "number_range":
                    if isinstance(val, dict):
                        if val.get("min") is not None:
                            card_where.append(f"{qualified} >= {val['min']}")
                        if val.get("max") is not None:
                            card_where.append(f"{qualified} <= {val['max']}")

            where_sql = "WHERE " + " AND ".join(card_where) if card_where else "WHERE 1=1"
            query = query.replace("{WHERE}", where_sql)

            try:
                res = conn.execute(query)
                columns = [d[0] for d in res.description]
                rows = res.fetchall()
                safe_rows = []
                for row in rows:
                    safe_row = []
                    for v in row:
                        if v is None:
                            safe_row.append(None)
                        elif hasattr(v, 'item'):
                            safe_row.append(v.item())
                        elif isinstance(v, (int, float, str, bool)):
                            safe_row.append(v)
                        else:
                            safe_row.append(str(v))
                    safe_rows.append(safe_row)
                results.append({
                    "id": card.get("id", ""),
                    "type": card.get("type", "kpi"),
                    "title": card.get("title", ""),
                    "columns": columns,
                    "rows": safe_rows,
                    "chart_type": card.get("chart_type"),
                    "x": card.get("x"),
                    "y": card.get("y"),
                    "format": card.get("format", "number"),
                    "prefix": card.get("prefix", ""),
                    "suffix": card.get("suffix", ""),
                })
            except Exception as e:
                results.append({
                    "id": card.get("id", ""),
                    "type": "error",
                    "title": card.get("title", ""),
                    "error": str(e),
                })

        return {"cards": results}
    finally:
        conn.close()


@router.delete("/{slug}")
async def delete_dashboard(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dash = db.query(Dashboard).filter(Dashboard.slug == slug).first()
    if not dash:
        raise HTTPException(404, "Дашборд не найден")
    if dash.created_by != user.id and user.role != "admin":
        raise HTTPException(403, "Нет прав")
    dash.is_active = False
    db.commit()
    return {"ok": True}

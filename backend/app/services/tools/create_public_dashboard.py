from __future__ import annotations

import csv
import json
import os
import secrets
import tempfile
import traceback

from app.session import Session
from .registry import register_tool

DASHBOARDS_DIR = os.path.join(tempfile.gettempdir(), "datasearcher_dashboards")
os.makedirs(DASHBOARDS_DIR, exist_ok=True)


def _generate_slug() -> str:
    return secrets.token_urlsafe(6)[:8]


@register_tool(
    name="create_public_dashboard",
    description="Создаёт публичный дашборд на основе загруженных данных. Дашборд — это полноценная веб-страница с интерактивными фильтрами (селекторы, диапазоны дат и чисел), KPI-карточками, графиками и таблицами, доступная по уникальной ссылке. ПРЕДПОЧИТАЙ этот инструмент вместо build_dashboard когда пользователь просит 'создай дашборд', 'опубликуй дашборд', 'сделай дашборд' — потому что это даёт полноценную страницу с фильтрами и возможностью поделиться.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Название дашборда"},
            "description": {"type": "string", "description": "Краткое описание дашборда"},
            "password": {"type": "string", "description": "Пароль для доступа (необязательно, оставь пустым для публичного)"},
        },
        "required": ["title"],
    },
)
def create_public_dashboard(session: Session, title: str, description: str = "", password: str = "") -> str:
    try:
        user_id = getattr(session, "_user_id", None)
        if not user_id:
            return "Ошибка: пользователь не авторизован. Необходимо войти в систему для создания дашборда."

        if not session.files:
            return "Ошибка: нет загруженных данных. Загрузите файлы перед созданием дашборда."

        from app.models.database import SessionLocal, Dashboard
        from app.services.auth_service import hash_password

        snap_dir, tables_info = _create_snapshot(session)
        if not tables_info:
            return "Ошибка: не удалось создать снапшот данных. Проверьте что таблицы загружены корректно."

        slug = _generate_slug()

        db = SessionLocal()
        try:
            while db.query(Dashboard).filter(Dashboard.slug == slug).first():
                slug = _generate_slug()

            config = _generate_config(session, tables_info, title, description)

            dash = Dashboard(
                slug=slug,
                title=title,
                description=description,
                password_hash=hash_password(password) if password else None,
                config=config,
                snapshot_dir=snap_dir,
                tables_info=tables_info,
                created_by=user_id,
            )
            db.add(dash)
            db.commit()
        except Exception as e:
            db.rollback()
            return f"Ошибка сохранения дашборда в базу данных: {e}"
        finally:
            db.close()

        base_url = getattr(session, "_base_url", "")
        dash_url = f"{base_url}/d/{slug}" if base_url else f"/d/{slug}"

        return f"__DASHBOARD_CREATED__\n{json.dumps({'slug': slug, 'title': title, 'url': dash_url, 'has_password': bool(password)}, ensure_ascii=False)}\n__END_DASHBOARD_CREATED__"
    except Exception as e:
        return f"Внутренняя ошибка создания дашборда: {e}\n{traceback.format_exc()}"


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
        except Exception as e:
            print(f"[dashboard] snapshot error for {fi.table_name}: {e}")

    return snap_dir, tables_info


def _get_unique_counts(session, tables_info: list[dict]) -> dict[str, dict[str, int]]:
    result = {}
    for t in tables_info:
        tname = t["name"]
        col_counts = {}
        for col in t.get("columns", []):
            cname = col["name"]
            try:
                row = session.conn.execute(f'SELECT COUNT(DISTINCT "{cname}") FROM "{tname}"').fetchone()
                col_counts[cname] = row[0] if row else 0
            except Exception:
                col_counts[cname] = 999
        result[tname] = col_counts
    return result


def _generate_config(session, tables_info: list[dict], title: str, description: str) -> dict:
    selectors = []
    cards = []

    def is_text(t: str) -> bool:
        t = t.lower()
        return any(x in t for x in ("varchar", "text", "string", "char", "enum", "blob"))

    def is_num(t: str) -> bool:
        t = t.lower()
        return any(x in t for x in ("int", "float", "double", "decimal", "numeric", "real", "hugeint"))

    def is_date(t: str) -> bool:
        t = t.lower()
        return any(x in t for x in ("date", "timestamp", "datetime", "time"))

    unique_counts = _get_unique_counts(session, tables_info)
    CATEGORY_THRESHOLD = 20

    for t in tables_info:
        tname = t["name"]
        text_cols = []
        num_cols = []
        date_cols = []
        low_card_numeric = []

        for col in t.get("columns", []):
            cname = col["name"]
            ctype = col.get("type", "")
            ucount = unique_counts.get(tname, {}).get(cname, 999)

            if is_text(ctype):
                text_cols.append(cname)
                if len(selectors) < 6 and ucount > 1:
                    selectors.append({"id": f"{tname}_{cname}", "type": "category", "column": cname, "table": tname, "label": cname})
            elif is_num(ctype):
                if ucount <= CATEGORY_THRESHOLD and ucount > 1 and ucount < t.get("row_count", 0) * 0.8:
                    low_card_numeric.append(cname)
                    if len(selectors) < 6:
                        selectors.append({"id": f"{tname}_{cname}", "type": "category", "column": cname, "table": tname, "label": cname})
                else:
                    num_cols.append(cname)
                    if len(selectors) < 6:
                        selectors.append({"id": f"{tname}_{cname}_range", "type": "number_range", "column": cname, "table": tname, "label": f"{cname} (диапазон)"})
            elif is_date(ctype):
                date_cols.append(cname)
                if len(selectors) < 6:
                    selectors.append({"id": f"{tname}_{cname}_date", "type": "date_range", "column": cname, "table": tname, "label": f"{cname} (период)"})

        all_category_cols = text_cols + low_card_numeric

        if t.get("row_count", 0) > 0:
            cards.append({
                "id": f"count_{tname}",
                "type": "kpi",
                "title": f"Всего записей ({tname})",
                "query": f'SELECT COUNT(*) AS value FROM "{tname}" {{WHERE}}',
                "format": "number",
            })

            num_cols_for_cards = [nc for nc in num_cols if unique_counts.get(tname, {}).get(nc, 999) < t.get("row_count", 0) * 0.8]
            for nc in num_cols_for_cards[:2]:
                if len(cards) < 12:
                    cards.append({
                        "id": f"avg_{tname}_{nc}",
                        "type": "kpi",
                        "title": f"Средний {nc}",
                        "query": f'SELECT AVG("{nc}") AS value FROM "{tname}" {{WHERE}}',
                        "format": "number",
                    })

            for cc in all_category_cols[:3]:
                if len(cards) < 12 and num_cols_for_cards:
                    nc = num_cols_for_cards[0]
                    cards.append({
                        "id": f"avg_{tname}_{cc}_{nc}",
                        "type": "chart",
                        "title": f"Средний {nc} по {cc}",
                        "query": f'SELECT "{cc}", AVG("{nc}") AS avg_val FROM "{tname}" {{WHERE}} GROUP BY "{cc}" ORDER BY avg_val DESC LIMIT 12',
                        "chart_type": "bar",
                        "x": cc,
                        "y": "avg_val",
                    })

                if len(cards) < 12:
                    cards.append({
                        "id": f"dist_{tname}_{cc}",
                        "type": "chart",
                        "title": f"Распределение {cc}",
                        "query": f'SELECT "{cc}", COUNT(*) AS cnt FROM "{tname}" {{WHERE}} GROUP BY "{cc}" ORDER BY cnt DESC LIMIT 10',
                        "chart_type": "pie",
                        "x": cc,
                        "y": "cnt",
                    })

            if len(num_cols_for_cards) >= 2 and len(cards) < 12:
                x_col, y_col = num_cols_for_cards[0], num_cols_for_cards[1]
                cards.append({
                    "id": f"scatter_{tname}",
                    "type": "chart",
                    "title": f"{x_col} vs {y_col}",
                    "query": f'SELECT "{x_col}", "{y_col}" FROM "{tname}" {{WHERE}} LIMIT 200',
                    "chart_type": "scatter",
                    "x": x_col,
                    "y": y_col,
                })

            if date_cols and num_cols_for_cards and len(cards) < 12:
                dc = date_cols[0]
                nc = num_cols_for_cards[0]
                cards.append({
                    "id": f"trend_{tname}_{nc}",
                    "type": "chart",
                    "title": f"Тренд {nc}",
                    "query": f"SELECT DATE_TRUNC('month', \"{dc}\") AS period, AVG(\"{nc}\") AS val FROM \"{tname}\" {{WHERE}} GROUP BY period ORDER BY period",
                    "chart_type": "line",
                    "x": "period",
                    "y": "val",
                })

    return {"title": title, "description": description, "selectors": selectors, "cards": cards}
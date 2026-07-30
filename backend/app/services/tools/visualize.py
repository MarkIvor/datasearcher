from __future__ import annotations

import json
import math
from datetime import date, datetime

from app.session import Session
from .registry import format_table, register_tool


def _safe_val(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    try:
        if hasattr(v, "item"):
            return v.item()
    except Exception:
        pass
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        pass
    if isinstance(v, (date, datetime)):
        return str(v)
    return str(v)


@register_tool(
    name="visualize_data",
    description="Визуализация данных: создаёт интерактивный график (bar, line, pie, scatter, area, histogram) из SQL-запроса или данных таблицы. Результат отображается как график прямо в чате.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "chart_type": {"type": "string", "enum": ["bar", "line", "pie", "scatter", "area", "histogram"], "description": "Тип графика"},
            "title": {"type": "string", "description": "Заголовок графика"},
            "x_column": {"type": "string", "description": "Колонка для оси X (или категории для pie)"},
            "y_columns": {"type": "string", "description": "Колонки для оси Y через запятую (или значение для pie)"},
            "sql": {"type": "string", "description": "SQL-запрос для подготовки данных (необязательно, если простая агрегация)"},
            "limit": {"type": "integer", "description": "Максимальное количество точек данных (по умолчанию 50)"},
        },
        "required": ["table_name", "chart_type", "title", "x_column", "y_columns"],
    },
)
def visualize_data(
    session: Session,
    table_name: str,
    chart_type: str,
    title: str,
    x_column: str,
    y_columns: str,
    sql: str = "",
    limit: int = 50,
) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn
    y_cols = [c.strip() for c in y_columns.split(",")]

    if sql.strip():
        try:
            result = conn.execute(sql.strip())
            col_names = [d[0] for d in result.description]
            rows = result.fetchmany(limit)
        except Exception as e:
            return f"Ошибка SQL: {e}"
    else:
        if chart_type == "histogram":
            col = y_cols[0] if y_cols else x_column
            try:
                mn_mx = conn.execute(f'SELECT MIN("{col}"), MAX("{col}") FROM "{table_name}" WHERE "{col}" IS NOT NULL').fetchone()
                if not mn_mx or mn_mx[0] is None:
                    return f"Нет данных в колонке {col}"
                mn, mx = _safe_val(mn_mx[0]), _safe_val(mn_mx[1])
                n_bins = min(limit, 20)
                width = (mx - mn) / n_bins if mx != mn else 1
                result = conn.execute(
                    f'SELECT FLOOR(("{col}" - {mn}) / {width}) * {width} + {mn} as bin_start, '
                    f'COUNT(*) as freq '
                    f'FROM "{table_name}" WHERE "{col}" IS NOT NULL '
                    f'GROUP BY bin_start ORDER BY bin_start LIMIT {limit}'
                )
                col_names = [d[0] for d in result.description]
                rows = result.fetchall()
                x_column = "bin_start"
                y_cols = ["freq"]
            except Exception as e:
                return f"Ошибка: {e}"
        else:
            y_agg = ", ".join(f'SUM("{c}") as "{c}"' for c in y_cols)
            try:
                q = f'SELECT "{x_column}", {y_agg} FROM "{table_name}" GROUP BY "{x_column}" ORDER BY "{x_column}" LIMIT {limit}'
                result = conn.execute(q)
                col_names = [d[0] for d in result.description]
                rows = result.fetchall()
            except Exception as e:
                return f"Ошибка: {e}"

    if not rows:
        return "Нет данных для визуализации."

    data = []
    for row in rows:
        point = {}
        for i, col in enumerate(col_names):
            point[col] = _safe_val(row[i])
        data.append(point)

    chart_spec = {
        "type": chart_type,
        "title": title,
        "data": data,
        "xKey": x_column,
        "yKeys": y_cols,
    }

    return f"__CHART_DATA__\n{json.dumps(chart_spec, ensure_ascii=False, default=str)}\n__END_CHART_DATA__"

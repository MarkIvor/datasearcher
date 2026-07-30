from __future__ import annotations

import json
import math
from datetime import date, datetime

from app.session import Session
from .registry import register_tool


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
    name="build_dashboard",
    description="Автоматический дашборд: генерирует набор из 4-6 ключевых графиков одним вызовом. Покажи все основные метрики, распределения, тренды и связи в виде коллекции чартов.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "focus": {"type": "string", "description": "Фокус дашборда (необязательно: продажи, клиенты, финансы, качество)"},
        },
        "required": ["table_name"],
    },
)
def build_dashboard(session: Session, table_name: str, focus: str = "") -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn
    schema = conn.execute(f'DESCRIBE "{table_name}"').fetchall()
    count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]

    if count == 0:
        return f"Таблица {table_name} пуста."

    numeric_types = {"integer", "bigint", "smallint", "float", "double", "decimal", "numeric", "real", "hugeint"}
    string_types = {"varchar", "text", "char", "string"}
    date_types = {"date", "timestamp", "timestamptz", "datetime"}

    numeric_cols = [s[0] for s in schema if any(t in s[1].lower() for t in numeric_types)]
    string_cols = [s[0] for s in schema if any(t in s[1].lower() for t in string_types)]
    date_cols = [s[0] for s in schema if any(t in s[1].lower() for t in date_types)]

    charts = []
    out = [f"# Дашборд: {table_name}", f"**{count:,} строк**, {len(schema)} колонок", ""]

    # 1. Distribution of first numeric col (histogram)
    if numeric_cols:
        col = numeric_cols[0]
        try:
            mn_mx = conn.execute(f'SELECT MIN("{col}"), MAX("{col}") FROM "{table_name}" WHERE "{col}" IS NOT NULL').fetchone()
            if mn_mx and mn_mx[0] is not None:
                mn, mx = mn_mx
                n_bins = 15
                width = (mx - mn) / n_bins if mx != mn else 1
                hist = conn.execute(
                    f'SELECT FLOOR(("{col}" - {mn}) / {width}) * {width} + {mn} as bin, COUNT(*) as freq '
                    f'FROM "{table_name}" WHERE "{col}" IS NOT NULL GROUP BY bin ORDER BY bin'
                ).fetchall()
                chart_data = [{"bin": _safe_val(r[0]), "freq": _safe_val(r[1])} for r in hist]
                charts.append({
                    "type": "histogram",
                    "title": f"Распределение: {col}",
                    "data": chart_data,
                    "xKey": "bin",
                    "yKeys": ["freq"],
                })
        except Exception:
            pass

    # 2. Top categories for first string col (bar chart)
    if string_cols:
        col = string_cols[0]
        try:
            top = conn.execute(
                f'SELECT "{col}", COUNT(*) as cnt FROM "{table_name}" '
                f'WHERE "{col}" IS NOT NULL GROUP BY "{col}" ORDER BY cnt DESC LIMIT 10'
            ).fetchall()
            if len(top) >= 2:
                chart_data = [{"name": str(r[0])[:20], "count": _safe_val(r[1])} for r in top]
                charts.append({
                    "type": "bar",
                    "title": f"Топ категорий: {col}",
                    "data": chart_data,
                    "xKey": "name",
                    "yKeys": ["count"],
                })
        except Exception:
            pass

    # 3. Time trend (if dates exist)
    if date_cols and numeric_cols:
        date_col = date_cols[0]
        val_col = numeric_cols[0]
        try:
            trend = conn.execute(
                f"SELECT DATE_TRUNC('month', \"{date_col}\") as m, "
                f'AVG("{val_col}") as v '
                f'FROM "{table_name}" WHERE "{date_col}" IS NOT NULL '
                f'GROUP BY m ORDER BY m'
            ).fetchall()
        except Exception:
            trend = []

        if len(trend) >= 3:
            chart_data = [{"period": str(r[0])[:10], "value": _safe_val(r[1])} for r in trend if r[1] is not None]
            charts.append({
                "type": "line",
                "title": f"Тренд: {val_col}",
                "data": chart_data,
                "xKey": "period",
                "yKeys": ["value"],
            })

    # 4. Pie chart for second string col or same if only one
    if len(string_cols) >= 1:
        pie_col = string_cols[1] if len(string_cols) > 1 else string_cols[0]
        try:
            pie_data = conn.execute(
                f'SELECT "{pie_col}", COUNT(*) as cnt FROM "{table_name}" '
                f'WHERE "{pie_col}" IS NOT NULL GROUP BY "{pie_col}" ORDER BY cnt DESC LIMIT 8'
            ).fetchall()
            if len(pie_data) >= 2:
                chart_data = [{"name": str(r[0])[:20], "value": _safe_val(r[1])} for r in pie_data]
                charts.append({
                    "type": "pie",
                    "title": f"Состав: {pie_col}",
                    "data": chart_data,
                    "xKey": "name",
                    "yKeys": ["value"],
                })
        except Exception:
            pass

    # 5. Scatter if 2+ numeric cols
    if len(numeric_cols) >= 2:
        x_col, y_col = numeric_cols[0], numeric_cols[1]
        try:
            scatter = conn.execute(
                f'SELECT "{x_col}", "{y_col}" FROM "{table_name}" '
                f'WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL LIMIT 200'
            ).fetchall()
            if len(scatter) >= 5:
                chart_data = [{x_col: _safe_val(r[0]), y_col: _safe_val(r[1])} for r in scatter]
                charts.append({
                    "type": "scatter",
                    "title": f"{x_col} vs {y_col}",
                    "data": chart_data,
                    "xKey": x_col,
                    "yKeys": [y_col],
                })
        except Exception:
            pass

    # 6. Correlation heatmap as bar chart of top correlations
    if len(numeric_cols) >= 3:
        corrs = []
        for i, col_a in enumerate(numeric_cols[:8]):
            for col_b in numeric_cols[i + 1:8]:
                try:
                    r = conn.execute(
                        f'SELECT CORR("{col_a}", "{col_b}") FROM "{table_name}" '
                        f'WHERE "{col_a}" IS NOT NULL AND "{col_b}" IS NOT NULL'
                    ).fetchone()[0]
                    if r is not None and abs(r) > 0.3:
                        corrs.append({"pair": f"{col_a[:8]}-{col_b[:8]}", "correlation": _safe_val(r)})
                except Exception:
                    pass
        if corrs:
            corrs.sort(key=lambda x: -abs(x["correlation"]))
            charts.append({
                "type": "bar",
                "title": "Корреляции",
                "data": corrs[:10],
                "xKey": "pair",
                "yKeys": ["correlation"],
            })

    out.append(f"Сгенерировано {len(charts)} графиков:")
    for i, chart in enumerate(charts, 1):
        out.append(f"  {i}. {chart['title']} ({chart['type']})")

    out.append("")

    for chart_spec in charts:
        out.append(f"__CHART_DATA__\n{json.dumps(chart_spec, ensure_ascii=False, default=str)}\n__END_CHART_DATA__")
        out.append("")

    return "\n".join(out)

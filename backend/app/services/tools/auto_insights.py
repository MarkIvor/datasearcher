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
    name="auto_insights",
    description="Авто-инсайты: магическая кнопка, которая автоматически запускает корреляции, аномалии, тренды, распределения и выдаёт топ-5 самых интересных находок с графиками. Один вызов — полная картина данных.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "focus": {"type": "string", "description": "На чём сфокусироваться (необязательно: продажи, клиенты, тренды, качество)"},
        },
        "required": ["table_name"],
    },
)
def auto_insights(session: Session, table_name: str, focus: str = "") -> str:
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

    insights = []
    charts = []

    # 1. Nulls & quality
    worst_null_col = None
    worst_null_pct = 0
    for row in schema:
        col_name = row[0]
        null_count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}" WHERE "{col_name}" IS NULL').fetchone()[0]
        null_pct = round(null_count / count * 100, 1) if count else 0
        if null_pct > worst_null_pct:
            worst_null_pct = null_pct
            worst_null_col = col_name
    if worst_null_pct > 20:
        insights.append(f"⚠️ **{worst_null_col}** имеет {worst_null_pct}% пропусков — может исказить аналитику")

    # 2. Correlations
    if len(numeric_cols) >= 2:
        strong_corrs = []
        for i, col_a in enumerate(numeric_cols[:10]):
            for col_b in numeric_cols[i + 1:10]:
                try:
                    r = conn.execute(
                        f'SELECT CORR("{col_a}", "{col_b}") FROM "{table_name}" '
                        f'WHERE "{col_a}" IS NOT NULL AND "{col_b}" IS NOT NULL'
                    ).fetchone()[0]
                    if r is not None and abs(r) > 0.5:
                        strong_corrs.append((col_a, col_b, round(r, 3)))
                except Exception:
                    pass
        if strong_corrs:
            strong_corrs.sort(key=lambda x: -abs(x[2]))
            for a, b, r in strong_corrs[:3]:
                direction = "положительная" if r > 0 else "отрицательная"
                insights.append(f"🔗 **{a}** и **{b}** имеют {direction} корреляцию (r={r:+.3f})")
            if len(strong_corrs) >= 2:
                chart_data = [{"pair": f"{a}-{b}", "correlation": _safe_val(r)} for a, b, r in strong_corrs[:10]]
                charts.append({
                    "type": "bar",
                    "title": "Сильные корреляции",
                    "data": chart_data,
                    "xKey": "pair",
                    "yKeys": ["correlation"],
                })

    # 3. Outliers
    for col in numeric_cols[:6]:
        try:
            stats_row = conn.execute(
                f'SELECT AVG("{col}"), STDDEV("{col}") FROM "{table_name}" WHERE "{col}" IS NOT NULL'
            ).fetchone()
            if stats_row and stats_row[1]:
                mean, stddev = stats_row
                outlier_count = conn.execute(
                    f'SELECT COUNT(*) FROM "{table_name}" '
                    f'WHERE ABS(("{col}" - {mean}) / {stddev}) > 3'
                ).fetchone()[0]
                if outlier_count > 0 and outlier_count < count * 0.1:
                    insights.append(f"🚨 **{col}**: {outlier_count} выбросов (z-score > 3)")
        except Exception:
            pass

    # 4. Time trends
    if date_cols and numeric_cols:
        date_col = date_cols[0]
        val_col = numeric_cols[0]
        try:
            trend_rows = conn.execute(
                f"SELECT DATE_TRUNC('month', \"{date_col}\") as m, "
                f'AVG("{val_col}") as v '
                f'FROM "{table_name}" WHERE "{date_col}" IS NOT NULL '
                f'GROUP BY m ORDER BY m'
            ).fetchall()
            if len(trend_rows) >= 3:
                import numpy as np
                vals = [float(r[1]) for r in trend_rows if r[1] is not None]
                if vals:
                    first, last = vals[0], vals[-1]
                    if first != 0:
                        change = ((last - first) / abs(first)) * 100
                        if abs(change) > 10:
                            direction = "рост" if change > 0 else "падение"
                            insights.append(f"📈 **{val_col}**: {direction} на {abs(round(change, 1))}% за период")
                        chart_data = [
                            {"period": str(r[0])[:10], "value": _safe_val(r[1])}
                            for r in trend_rows if r[1] is not None
                        ]
                        charts.append({
                            "type": "line",
                            "title": f"Тренд: {val_col}",
                            "data": chart_data,
                            "xKey": "period",
                            "yKeys": ["value"],
                        })
        except Exception:
            pass

    # 5. Top categories
    for col in string_cols[:3]:
        try:
            top = conn.execute(
                f'SELECT "{col}", COUNT(*) as cnt FROM "{table_name}" '
                f'WHERE "{col}" IS NOT NULL GROUP BY "{col}" ORDER BY cnt DESC LIMIT 5'
            ).fetchall()
            if top:
                distinct = conn.execute(
                    f'SELECT COUNT(DISTINCT "{col}") FROM "{table_name}" WHERE "{col}" IS NOT NULL'
                ).fetchone()[0]
                top_pct = round(top[0][1] / count * 100, 1) if count else 0
                if top_pct > 30:
                    insights.append(f"🏷️ **{col}**: \"{top[0][0]}\" доминирует ({top_pct}% всех записей, {distinct} уникальных)")
                    chart_data = [{"name": str(r[0]), "count": _safe_val(r[1])} for r in top]
                    charts.append({
                        "type": "pie",
                        "title": f"Распределение: {col}",
                        "data": chart_data,
                        "xKey": "name",
                        "yKeys": ["count"],
                    })
        except Exception:
            pass

    # 6. Distribution shape
    for col in numeric_cols[:4]:
        try:
            skew = conn.execute(f'SELECT SKEWNESS("{col}") FROM "{table_name}" WHERE "{col}" IS NOT NULL').fetchone()[0]
            if skew is not None and abs(skew) > 1.5:
                direction = "право" if skew > 0 else "лево"
                insights.append(f"📊 **{col}**: сильная асимметрия (skew={round(skew, 2)}), скошено {direction}")
        except Exception:
            pass

    if not insights:
        insights.append("✅ Данные выглядят чистыми и без ярких аномалий. Попробуйте более глубокий анализ отдельными инструментами.")

    out = [f"# Авто-инсайты: {table_name}", f"**{count:,} строк**, {len(schema)} колонок", ""]
    for i, insight in enumerate(insights[:8], 1):
        out.append(f"{i}. {insight}")
    out.append("")

    for chart_spec in charts[:3]:
        out.append(f"__CHART_DATA__\n{json.dumps(chart_spec, ensure_ascii=False, default=str)}\n__END_CHART_DATA__")
        out.append("")

    return "\n".join(out)

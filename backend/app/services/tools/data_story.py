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
    name="data_story",
    description="Data Story: ИИ генерирует нарратив с графиками — связный рассказ о данных с визуализациями. 'Расскажи историю данных' → 3-5 инсайтов с чартами и подписями. Идеально для презентаций.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "theme": {"type": "string", "description": "Тема истории (необязательно): продажи, клиенты, качество, тренды, обзор"},
        },
        "required": ["table_name"],
    },
)
def data_story(session: Session, table_name: str, theme: str = "") -> str:
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
    story_parts = []

    story_parts.append(f"# 📖 История данных: {table_name}")
    story_parts.append(f"*{count:,} записей, {len(schema)} параметров*\n")

    # Chapter 1: What are we looking at?
    story_parts.append("## Глава 1: Что перед нами?")
    story_parts.append(f"Таблица содержит **{count:,}** записей с **{len(numeric_cols)}** числовыми и **{len(string_cols)}** категориальными параметрами.")
    if date_cols:
        date_col = date_cols[0]
        try:
            dr = conn.execute(f'SELECT MIN("{date_col}"), MAX("{date_col}") FROM "{table_name}" WHERE "{date_col}" IS NOT NULL').fetchone()
            if dr and dr[0]:
                story_parts.append(f"Данные охватывают период с **{dr[0]}** по **{dr[1]}**.")
        except Exception:
            pass
    story_parts.append("")

    # Chapter 2: The shape of numbers
    if numeric_cols:
        story_parts.append("## Глава 2: Форма чисел")
        col = numeric_cols[0]
        try:
            stats = conn.execute(
                f'SELECT AVG("{col}"), STDDEV("{col}"), SKEWNESS("{col}"), '
                f'MIN("{col}"), MAX("{col}") FROM "{table_name}" WHERE "{col}" IS NOT NULL'
            ).fetchone()
            if stats and stats[0] is not None:
                avg, std, skew, mn, mx = stats
                story_parts.append(f"Среднее **{col}** = **{round(avg, 2)}** (диапазон {mn}–{mx}).")
                if skew is not None and abs(skew) > 1:
                    story_parts.append(f"Распределение скошено ({'вправо — много малых значений и хвост больших' if skew > 0 else 'влево'}).")
                else:
                    story_parts.append("Распределение близко к симметричному.")

                mn_val = conn.execute(f'SELECT MIN("{col}") FROM "{table_name}" WHERE "{col}" IS NOT NULL').fetchone()[0]
                mx_val = conn.execute(f'SELECT MAX("{col}") FROM "{table_name}" WHERE "{col}" IS NOT NULL').fetchone()[0]
                n_bins = 15
                width = (mx_val - mn_val) / n_bins if mx_val != mn_val else 1
                hist = conn.execute(
                    f'SELECT FLOOR(("{col}" - {mn_val}) / {width}) * {width} + {mn_val} as bin, COUNT(*) as freq '
                    f'FROM "{table_name}" WHERE "{col}" IS NOT NULL GROUP BY bin ORDER BY bin'
                ).fetchall()
                charts.append({
                    "type": "area",
                    "title": f"Как распределены {col}",
                    "data": [{"bin": _safe_val(r[0]), "freq": _safe_val(r[1])} for r in hist],
                    "xKey": "bin",
                    "yKeys": ["freq"],
                })
        except Exception:
            pass
        story_parts.append("")

    # Chapter 3: Groups and categories
    if string_cols:
        story_parts.append("## Глава 3: Кто в главной роли?")
        col = string_cols[0]
        try:
            top = conn.execute(
                f'SELECT "{col}", COUNT(*) as cnt FROM "{table_name}" '
                f'WHERE "{col}" IS NOT NULL GROUP BY "{col}" ORDER BY cnt DESC LIMIT 8'
            ).fetchall()
            if top:
                leader = top[0]
                leader_pct = round(leader[1] / count * 100, 1)
                story_parts.append(f"**{leader[0]}** лидирует с {leader_pct}% записей.")
                if len(top) >= 3:
                    story_parts.append(f"За ним следуют **{top[1][0]}** и **{top[2][0]}**.")

                charts.append({
                    "type": "pie",
                    "title": f"Кто сколько: {col}",
                    "data": [{"name": str(r[0])[:20], "value": _safe_val(r[1])} for r in top],
                    "xKey": "name",
                    "yKeys": ["value"],
                })
        except Exception:
            pass
        story_parts.append("")

    # Chapter 4: Trends over time
    if date_cols and numeric_cols:
        story_parts.append("## Глава 4: Куда всё движется?")
        date_col = date_cols[0]
        val_col = numeric_cols[0]
        try:
            trend = conn.execute(
                f"SELECT DATE_TRUNC('month', \"{date_col}\") as m, "
                f'AVG("{val_col}") as v '
                f'FROM "{table_name}" WHERE "{date_col}" IS NOT NULL '
                f'GROUP BY m ORDER BY m'
            ).fetchall()
            if len(trend) >= 3:
                first, last = trend[0][1], trend[-1][1]
                if first and last and first != 0:
                    change = ((last - first) / abs(first)) * 100
                    if change > 10:
                        story_parts.append(f"Мы видим **рост на {round(change, 1)}%** за весь период.")
                    elif change < -10:
                        story_parts.append(f"Наблюдается **падение на {abs(round(change, 1))}%**.")
                    else:
                        story_parts.append("Показатель остаётся **стабильным**.")

                    peak = max(trend, key=lambda x: x[1] if x[1] else 0)
                    story_parts.append(f"Пик пришёлся на **{str(peak[0])[:10]}** ({round(float(peak[1]), 2)}).")

                chart_data = [{"period": str(r[0])[:10], "value": _safe_val(r[1])} for r in trend if r[1] is not None]
                charts.append({
                    "type": "line",
                    "title": f"Динамика: {val_col}",
                    "data": chart_data,
                    "xKey": "period",
                    "yKeys": ["value"],
                })
        except Exception:
            pass
        story_parts.append("")

    # Chapter 5: Hidden connections
    if len(numeric_cols) >= 2:
        story_parts.append("## Глава 5: Скрытые связи")
        strong = []
        for i, col_a in enumerate(numeric_cols[:8]):
            for col_b in numeric_cols[i + 1:8]:
                try:
                    r = conn.execute(
                        f'SELECT CORR("{col_a}", "{col_b}") FROM "{table_name}" '
                        f'WHERE "{col_a}" IS NOT NULL AND "{col_b}" IS NOT NULL'
                    ).fetchone()[0]
                    if r is not None and abs(r) > 0.5:
                        strong.append((col_a, col_b, round(r, 3)))
                except Exception:
                    pass
        if strong:
            strong.sort(key=lambda x: -abs(x[2]))
            for a, b, r in strong[:3]:
                direction = "растут вместе" if r > 0 else "одна растёт, другая падает"
                story_parts.append(f"**{a}** и **{b}** {direction} (r={r:+.3f}).")
            if len(strong) >= 2:
                charts.append({
                    "type": "bar",
                    "title": "Скрытые связи",
                    "data": [{"pair": f"{a[:10]}↔{b[:10]}", "correlation": _safe_val(r)} for a, b, r in strong[:8]],
                    "xKey": "pair",
                    "yKeys": ["correlation"],
                })
        else:
            story_parts.append("Явных связей между числовыми показателями не обнаружено — каждый живёт своей жизнью.")
        story_parts.append("")

    story_parts.append("---")
    story_parts.append("*Это автоматическая история, основанная на статистическом анализе данных. Для более глубоких выводов используйте специализированные инструменты.*")

    out = story_parts
    out.append("")
    for chart_spec in charts[:5]:
        out.append(f"__CHART_DATA__\n{json.dumps(chart_spec, ensure_ascii=False, default=str)}\n__END_CHART_DATA__")
        out.append("")

    return "\n".join(out)

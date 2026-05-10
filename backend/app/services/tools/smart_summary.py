from __future__ import annotations

from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="smart_summary",
    description="Умное саммари таблицы: автоматически определяет ключевые метрики, топ-группы, выбросы, паттерны и аномалии. Один вызов — полная картина данных. Идеально для первого знакомства с данными.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "focus": {"type": "string", "description": "На чём сфокусироваться (необязательно, например: 'продажи', 'клиенты', 'тренды')"},
        },
        "required": ["table_name"],
    },
)
def smart_summary(session: Session, table_name: str, focus: str = "") -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn
    schema = conn.execute(f'DESCRIBE "{table_name}"').fetchall()
    count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]

    if count == 0:
        return f"Таблица {table_name} пуста."

    out = [f"# Саммари: {table_name}", f"**{count:,} строк**, {len(schema)} колонок", ""]

    numeric_types = {"integer", "bigint", "smallint", "float", "double", "decimal", "numeric", "real", "hugeint"}
    string_types = {"varchar", "text", "char", "string"}
    date_types = {"date", "timestamp", "timestamptz", "datetime"}

    numeric_cols = [s for s in schema if any(t in s[1].lower() for t in numeric_types)]
    string_cols = [s for s in schema if any(t in s[1].lower() for t in string_types)]
    date_cols = [s for s in schema if any(t in s[1].lower() for t in date_types)]

    if numeric_cols:
        out.append("## Ключевые метрики")
        for col_name, col_type in numeric_cols[:8]:
            try:
                stats = conn.execute(
                    f'SELECT AVG("{col_name}"), SUM("{col_name}"), MIN("{col_name}"), MAX("{col_name}"), '
                    f'STDDEV("{col_name}"), COUNT(DISTINCT "{col_name}") '
                    f'FROM "{table_name}" WHERE "{col_name}" IS NOT NULL'
                ).fetchone()
                avg_v, total_v, min_v, max_v, std_v, distinct_v = stats
                out.append(f"**{col_name}**: avg={round(avg_v, 2) if avg_v else 'N/A'}, "
                          f"sum={round(total_v, 2) if total_v else 'N/A'}, "
                          f"range=[{min_v} .. {max_v}], "
                          f"distinct={distinct_v}")
            except Exception:
                pass
        out.append("")

    if string_cols:
        out.append("## Топ группы")
        for col_name, col_type in string_cols[:5]:
            try:
                top = conn.execute(
                    f'SELECT "{col_name}", COUNT(*) as cnt FROM "{table_name}" '
                    f'WHERE "{col_name}" IS NOT NULL GROUP BY "{col_name}" ORDER BY cnt DESC LIMIT 5'
                ).fetchall()
                if top:
                    groups = ", ".join(f"{v} ({c:,})" for v, c in top)
                    distinct = conn.execute(
                        f'SELECT COUNT(DISTINCT "{col_name}") FROM "{table_name}" WHERE "{col_name}" IS NOT NULL'
                    ).fetchone()[0]
                    out.append(f"**{col_name}** ({distinct} уникальных): {groups}")
            except Exception:
                pass
        out.append("")

    if numeric_cols:
        out.append("## Потенциальные аномалии")
        anomaly_found = False
        for col_name, col_type in numeric_cols[:6]:
            try:
                stats = conn.execute(
                    f'SELECT AVG("{col_name}"), STDDEV("{col_name}"), '
                    f'PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY "{col_name}"), '
                    f'PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY "{col_name}") '
                    f'FROM "{table_name}" WHERE "{col_name}" IS NOT NULL'
                ).fetchone()
                mean, stddev, q1, q3 = stats
                if stddev and stddev > 0:
                    outlier_count = conn.execute(
                        f'SELECT COUNT(*) FROM "{table_name}" '
                        f'WHERE ABS(("{col_name}" - {mean}) / {stddev}) > 3'
                    ).fetchone()[0]
                    if outlier_count > 0:
                        anomaly_found = True
                        out.append(f"  - **{col_name}**: {outlier_count} выбросов (z-score > 3)")
                if q1 is not None and q3 is not None:
                    iqr = q3 - q1
                    if iqr > 0:
                        iqr_outliers = conn.execute(
                            f'SELECT COUNT(*) FROM "{table_name}" '
                            f'WHERE "{col_name}" < {q1 - 1.5 * iqr} OR "{col_name}" > {q3 + 1.5 * iqr}'
                        ).fetchone()[0]
                        if iqr_outliers > 0:
                            anomaly_found = True
                            out.append(f"  - **{col_name}**: {iqr_outliers} выбросов (IQR method)")
            except Exception:
                pass
        if not anomaly_found:
            out.append("Явных аномалий не обнаружено.")
        out.append("")

    if string_cols:
        out.append("## Пропуски и качество")
        quality_issues = []
        for col_name, col_type in schema:
            null_count = conn.execute(
                f'SELECT COUNT(*) FROM "{table_name}" WHERE "{col_name}" IS NULL'
            ).fetchone()[0]
            null_pct = round(null_count / count * 100, 1) if count else 0
            if null_pct > 5:
                quality_issues.append(f"  - **{col_name}**: {null_pct}% пропусков")
        if quality_issues:
            out.extend(quality_issues)
        else:
            out.append("Пропуски минимальны — данные выглядят полными.")
        out.append("")

    if date_cols and numeric_cols:
        date_col = date_cols[0][0]
        val_col = numeric_cols[0][0]
        try:
            trend = conn.execute(
                f'SELECT MIN("{date_col}"), MAX("{date_col}"), '
                f"COUNT(DISTINCT DATE_TRUNC('month', \"{date_col}\")) as months "
                f'FROM "{table_name}" WHERE "{date_col}" IS NOT NULL'
            ).fetchone()
            if trend and trend[0]:
                out.append("## Временной охват")
                out.append(f"Период: {trend[0]} — {trend[1]} ({trend[2]} месяцев)")
                out.append("")
        except Exception:
            pass

    out.append("## Рекомендации по анализу")
    if numeric_cols and string_cols:
        out.append(f"- Используй `correlation_analysis` для поиска связей между числовыми колонками")
    if string_cols and len(string_cols) >= 2:
        out.append(f"- Используй `cross_tab` для анализа связей между категориями")
    if date_cols:
        out.append(f"- Используй `time_analysis` для изучения динамики по времени")
    if len(numeric_cols) >= 2:
        out.append(f"- Используй `pivot_table` для создания сводных таблиц")

    return "\n".join(out)

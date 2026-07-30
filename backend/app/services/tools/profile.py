from __future__ import annotations

from app.session import Session
from .registry import register_tool


@register_tool(
    name="profile_data",
    description="Профилирование данных: статистика по каждой колонке — null-процент, уникальность, min/max для чисел, top-5 значений для строк. Помогает быстро понять качество и распределение данных.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Имя таблицы для профилирования",
            },
            "columns": {
                "type": "string",
                "description": "Список колонок через запятую (необязательно, по умолчанию все)",
            },
        },
        "required": ["table_name"],
    },
)
def profile_data(session: Session, table_name: str, columns: str = "") -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn
    count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
    if count == 0:
        return f"Таблица {table_name} пуста."

    schema = conn.execute(f'DESCRIBE "{table_name}"').fetchall()
    if columns.strip():
        col_names = [c.strip() for c in columns.split(",")]
        schema = [s for s in schema if s[0] in col_names]
    else:
        col_names = [s[0] for s in schema]

    results = []
    for row in schema:
        col_name, col_type = row[0], row[1]
        lines = [f"  {col_name} [{col_type}]"]

        null_count = conn.execute(
            f'SELECT COUNT(*) FROM "{table_name}" WHERE "{col_name}" IS NULL'
        ).fetchone()[0]
        null_pct = round(null_count / count * 100, 1) if count else 0
        lines.append(f"    null: {null_count} ({null_pct}%)")

        distinct = conn.execute(
            f'SELECT COUNT(DISTINCT "{col_name}") FROM "{table_name}"'
        ).fetchone()[0]
        unique_pct = round(distinct / count * 100, 1) if count else 0
        lines.append(f"    уникальных: {distinct} ({unique_pct}%)")

        col_type_lower = col_type.lower()
        if any(t in col_type_lower for t in ["int", "float", "double", "decimal", "numeric", "real"]):
            stats = conn.execute(
                f'SELECT MIN("{col_name}"), MAX("{col_name}"), AVG("{col_name}"), '
                f'STDDEV("{col_name}"), MEDIAN("{col_name}") FROM "{table_name}"'
            ).fetchone()
            lines.append(f"    min: {stats[0]}, max: {stats[1]}")
            lines.append(f"    avg: {round(stats[2], 2) if stats[2] else None}, "
                        f"stddev: {round(stats[3], 2) if stats[3] else None}, "
                        f"median: {stats[4]}")

            try:
                percentiles = conn.execute(
                    f'SELECT PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY "{col_name}"), '
                    f'PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY "{col_name}") '
                    f'FROM "{table_name}"'
                ).fetchone()
                lines.append(f"    Q1: {percentiles[0]}, Q3: {percentiles[1]}")
            except Exception:
                pass

        top5 = conn.execute(
            f'SELECT "{col_name}", COUNT(*) as cnt FROM "{table_name}" '
            f'WHERE "{col_name}" IS NOT NULL GROUP BY "{col_name}" ORDER BY cnt DESC LIMIT 5'
        ).fetchall()
        if top5:
            lines.append("    top-5: " + ", ".join(f"{v}({c})" for v, c in top5))

        results.append("\n".join(lines))

    header = f"Профиль таблицы: {table_name} ({count:,} строк)\n"
    return header + "\n".join(results)

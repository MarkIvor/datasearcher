from __future__ import annotations

from app.session import Session
from .registry import register_tool


@register_tool(
    name="detect_anomalies",
    description="Обнаружение аномалий (выбросов) в числовых колонках методами z-score и IQR. Помогает найти нетипичные значения, ошибки ввода, экстремальные значения.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Имя таблицы",
            },
            "columns": {
                "type": "string",
                "description": "Числовые колонки через запятую (необязательно, по умолчанию все числовые)",
            },
            "method": {
                "type": "string",
                "enum": ["zscore", "iqr", "both"],
                "description": "Метод обнаружения: zscore (отклонение от среднего), iqr (межквартильный размах), both (оба метода)",
            },
            "threshold": {
                "type": "number",
                "description": "Порог: для zscore — кол-во стандартных отклонений (по умолчанию 3), для IQR — множитель (по умолчанию 1.5)",
            },
        },
        "required": ["table_name"],
    },
)
def detect_anomalies(
    session: Session,
    table_name: str,
    columns: str = "",
    method: str = "both",
    threshold: float = 0,
) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn
    schema = conn.execute(f'DESCRIBE "{table_name}"').fetchall()

    numeric_types = {"integer", "bigint", "smallint", "float", "double", "decimal", "numeric", "real", "hugeint"}
    numeric_cols = [s[0] for s in schema if any(t in s[1].lower() for t in numeric_types)]

    if columns.strip():
        requested = [c.strip() for c in columns.split(",")]
        numeric_cols = [c for c in requested if c in numeric_cols]

    if not numeric_cols:
        return "Числовые колонки не найдены."

    results = []
    for col in numeric_cols:
        col_results = [f"  Колонка: {col}"]

        stats = conn.execute(
            f'SELECT AVG("{col}"), STDDEV("{col}"), '
            f'PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY "{col}"), '
            f'PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY "{col}") '
            f'FROM "{table_name}" WHERE "{col}" IS NOT NULL'
        ).fetchone()

        if not stats or stats[0] is None:
            col_results.append("    Недостаточно данных")
            results.append("\n".join(col_results))
            continue

        mean, stddev, q1, q3 = stats
        iqr = (q3 or 0) - (q1 or 0)

        if method in ("zscore", "both"):
            z_threshold = threshold if threshold > 0 else 3.0
            if stddev and stddev > 0:
                zscore_count = conn.execute(
                    f'SELECT COUNT(*) FROM "{table_name}" '
                    f'WHERE ABS(("{col}" - {mean}) / {stddev}) > {z_threshold}'
                ).fetchone()[0]
                col_results.append(
                    f"    Z-score (|z| > {z_threshold}): {zscore_count} аномалий "
                    f"(mean={round(mean, 2)}, stddev={round(stddev, 2)})"
                )
                if zscore_count > 0 and zscore_count <= 50:
                    outliers = conn.execute(
                        f'SELECT "{col}" FROM "{table_name}" '
                        f'WHERE ABS(("{col}" - {mean}) / {stddev}) > {z_threshold} '
                        f"ORDER BY \"{col}\" DESC LIMIT 20"
                    ).fetchall()
                    col_results.append(
                        f"    Значения: {', '.join(str(r[0]) for r in outliers)}"
                    )
            else:
                col_results.append("    Z-score: stddev=0, невозможно определить")

        if method in ("iqr", "both"):
            iqr_mult = threshold if threshold > 0 and method == "iqr" else 1.5
            lower = (q1 or 0) - iqr_mult * iqr
            upper = (q3 or 0) + iqr_mult * iqr
            iqr_count = conn.execute(
                f'SELECT COUNT(*) FROM "{table_name}" '
                f'WHERE "{col}" < {lower} OR "{col}" > {upper}'
            ).fetchone()[0]
            col_results.append(
                f"    IQR (x{iqr_mult}): {iqr_count} аномалий "
                f"(Q1={round(q1, 2)}, Q3={round(q3, 2)}, bounds=[{round(lower, 2)}, {round(upper, 2)}])"
            )
            if iqr_count > 0 and iqr_count <= 50:
                outliers = conn.execute(
                    f'SELECT "{col}" FROM "{table_name}" '
                    f'WHERE "{col}" < {lower} OR "{col}" > {upper} '
                    f'ORDER BY "{col}" DESC LIMIT 20'
                ).fetchall()
                col_results.append(
                    f"    Значения: {', '.join(str(r[0]) for r in outliers)}"
                )

        results.append("\n".join(col_results))

    header = f"Аномалии в таблице {table_name}:\n"
    return header + "\n".join(results)

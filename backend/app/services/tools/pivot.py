from __future__ import annotations

from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="pivot_table",
    description="Сводная таблица в стиле Excel: группировка по строкам, разворот по колонкам с агрегацией значений. Поддерживает sum/avg/count/min/max. Полный аналог Excel PivotTable.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "row_columns": {"type": "string", "description": "Колонки для строк (группировка) через запятую"},
            "col_column": {"type": "string", "description": "Колонка для столбцов (разворот)"},
            "value_column": {"type": "string", "description": "Колонка со значениями для агрегации"},
            "agg_function": {"type": "string", "enum": ["sum", "avg", "count", "min", "max"], "description": "Функция агрегации (по умолчанию sum)"},
        },
        "required": ["table_name", "row_columns", "col_column", "value_column"],
    },
)
def pivot_table(
    session: Session,
    table_name: str,
    row_columns: str,
    col_column: str,
    value_column: str,
    agg_function: str = "sum",
) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn
    row_cols = [c.strip() for c in row_columns.split(",")]

    agg_map = {"sum": "SUM", "avg": "AVG", "count": "COUNT", "min": "MIN", "max": "MAX"}
    agg_fn = agg_map.get(agg_function, "SUM")

    group_by = ", ".join(f'"{c}"' for c in row_cols)
    try:
        pivot_sql = (
            f'PIVOT "{table_name}" ON "{col_column}" '
            f'USING {agg_fn}("{value_column}") AS {agg_function} '
            f'GROUP BY {group_by}'
        )
        result = conn.execute(pivot_sql)
        columns = [d[0] for d in result.description]
        rows = result.fetchmany(200)
    except Exception as e:
        try:
            col_vals = conn.execute(
                f'SELECT DISTINCT "{col_column}" FROM "{table_name}" '
                f'WHERE "{col_column}" IS NOT NULL ORDER BY "{col_column}" LIMIT 20'
            ).fetchall()

            case_parts = []
            for (cv,) in col_vals:
                cv_escaped = str(cv).replace("'", "''")
                alias = f'"{cv}"'
                case_parts.append(
                    f'{agg_fn}(CASE WHEN "{col_column}" = \'{cv_escaped}\' THEN "{value_column}" END) AS {alias}'
                )

            group_by = ", ".join(f'"{c}"' for c in row_cols)
            sql = f'SELECT {group_by}, {", ".join(case_parts)} FROM "{table_name}" GROUP BY {group_by}'
            result = conn.execute(sql)
            columns = [d[0] for d in result.description]
            rows = result.fetchmany(200)
        except Exception as e2:
            return f"Ошибка создания сводной таблицы: {e2}"

    truncated = len(rows) == 200
    out = [
        f"Сводная таблица: {', '.join(row_cols)} × {col_column}",
        f"Значения: {agg_function}({value_column})",
        f"Строк: {len(rows)}{' (достигнут лимит)' if truncated else ''}",
        "",
        format_table(columns, rows),
    ]
    return "\n".join(out)

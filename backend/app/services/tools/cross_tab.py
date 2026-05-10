from __future__ import annotations

from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="cross_tab",
    description="Кросс-табуляция (таблица сопряжённости) двух категориальных колонок: частоты, проценты по строкам/столбцам. Анализ связей между категориями. Полезно для сегментации и выявления паттернов.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "row_column": {"type": "string", "description": "Колонка для строк (категориальная)"},
            "col_column": {"type": "string", "description": "Колонка для столбцов (категориальная)"},
            "value_column": {"type": "string", "description": "Колонка для агрегации значений (необязательно, по умолчанию подсчёт строк)"},
            "agg_function": {"type": "string", "enum": ["count", "sum", "avg", "min", "max"], "description": "Функция агрегации (по умолчанию count)"},
            "show_percent": {"type": "boolean", "description": "Показать проценты от общего (по умолчанию true)"},
        },
        "required": ["table_name", "row_column", "col_column"],
    },
)
def cross_tab(
    session: Session,
    table_name: str,
    row_column: str,
    col_column: str,
    value_column: str = "",
    agg_function: str = "count",
    show_percent: bool = True,
) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn

    row_vals = conn.execute(
        f'SELECT DISTINCT "{row_column}" FROM "{table_name}" WHERE "{row_column}" IS NOT NULL ORDER BY "{row_column}" LIMIT 30'
    ).fetchall()
    col_vals = conn.execute(
        f'SELECT DISTINCT "{col_column}" FROM "{table_name}" WHERE "{col_column}" IS NOT NULL ORDER BY "{col_column}" LIMIT 20'
    ).fetchall()

    if not row_vals or not col_vals:
        return "Нет данных для кросс-табуляции."

    row_labels = [str(r[0]) for r in row_vals]
    col_labels = [str(c[0]) for c in col_vals]

    agg_map = {"count": "COUNT(*)", "sum": f'SUM("{value_column}")', "avg": f'AVG("{value_column}")',
               "min": f'MIN("{value_column}")', "max": f'MAX("{value_column}")'}
    agg_expr = agg_map.get(agg_function, "COUNT(*)")

    matrix = []
    totals_row = []
    grand_total = 0

    for rv in row_vals:
        row_data = []
        for cv in col_vals:
            rv_escaped = str(rv[0]).replace("'", "''")
            cv_escaped = str(cv[0]).replace("'", "''")
            try:
                val = conn.execute(
                    f'SELECT {agg_expr} FROM "{table_name}" '
                    f'WHERE "{row_column}" = \'{rv_escaped}\' AND "{col_column}" = \'{cv_escaped}\''
                ).fetchone()[0]
                row_data.append(val if val is not None else 0)
            except Exception:
                row_data.append(0)
        matrix.append(row_data)
        row_total = sum(v for v in row_data if isinstance(v, (int, float)))
        totals_row.append(row_total)
        grand_total += row_total

    out = [f"Кросс-табуляция: {row_column} × {col_column}", ""]

    col_width = max(max(len(l) for l in col_labels), 8) + 2
    row_header_width = max(max(len(l) for l in row_labels), len(row_column)) + 2

    header = " " * row_header_width + "".join(l.center(col_width) for l in col_labels) + "Итого".center(col_width)
    out.append(header)
    out.append("-" * len(header))

    for i, label in enumerate(row_labels):
        row_total = totals_row[i]
        vals_str = ""
        for v in matrix[i]:
            if isinstance(v, float):
                vals_str += f"{v:.1f}".center(col_width)
            else:
                vals_str += str(v).center(col_width)

        pct_str = ""
        if show_percent and grand_total > 0 and isinstance(row_total, (int, float)):
            pct = round(row_total / grand_total * 100, 1)
            pct_str = f"{pct}%"

        line = label.ljust(row_header_width) + vals_str + str(row_total).center(col_width)
        if pct_str:
            line += pct_str.center(6)
        out.append(line)

    out.append("-" * len(header))
    total_line = "Итого".ljust(row_header_width)

    col_totals = []
    for j in range(len(col_labels)):
        ct = sum(matrix[i][j] for i in range(len(row_labels)) if isinstance(matrix[i][j], (int, float)))
        col_totals.append(ct)
        total_line += (str(round(ct, 1)) if isinstance(ct, float) else str(ct)).center(col_width)

    total_line += str(round(grand_total, 1) if isinstance(grand_total, float) else grand_total).center(col_width)
    out.append(total_line)

    if show_percent and grand_total > 0:
        out.append("")
        out.append("Проценты по строкам:")
        for i, label in enumerate(row_labels):
            row_total = totals_row[i]
            if row_total == 0:
                continue
            pcts = []
            for v in matrix[i]:
                if isinstance(v, (int, float)) and row_total:
                    pcts.append(f"{round(v / row_total * 100, 1)}%")
                else:
                    pcts.append("-")
            out.append(f"  {label}: {', '.join(pcts)}")

    out.append("")
    out.append(f"Всего записей: {grand_total}")
    out.append(f"Уникальных {row_column}: {len(row_labels)}")
    out.append(f"Уникальных {col_column}: {len(col_labels)}")

    if len(row_labels) > 1 and len(col_labels) > 1 and agg_function == "count":
        try:
            n = grand_total
            chi_sq = 0
            for i in range(len(row_labels)):
                for j in range(len(col_labels)):
                    expected = (totals_row[i] * col_totals[j]) / n if n else 0
                    observed = matrix[i][j] if isinstance(matrix[i][j], (int, float)) else 0
                    if expected > 0:
                        chi_sq += (observed - expected) ** 2 / expected
            df = (len(row_labels) - 1) * (len(col_labels) - 1)
            out.append(f"Хи-квадрат: {round(chi_sq, 2)}, df={df}")
            if chi_sq > 0:
                cramers_v = (chi_sq / (n * (min(len(row_labels), len(col_labels)) - 1))) ** 0.5 if n else 0
                strength = "слабая" if cramers_v < 0.3 else "умеренная" if cramers_v < 0.5 else "сильная"
                out.append(f"Cramer's V: {round(cramers_v, 4)} — {strength} связь между {row_column} и {col_column}")
        except Exception:
            pass

    return "\n".join(out)

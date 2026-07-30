from __future__ import annotations

from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="time_analysis",
    description="Анализ временных рядов: автоопределение date-колонок, тренд (линейная регрессия), рост/падение по периодам (день/неделя/месяц/год), скользящее среднее, сезонность. Показывает динамику изменения показателей во времени.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "date_column": {"type": "string", "description": "Колонка с датой/временем (автоопределение если не указана)"},
            "value_column": {"type": "string", "description": "Числовая колонка для анализа (автоопределение если не указана)"},
            "period": {"type": "string", "enum": ["day", "week", "month", "quarter", "year"], "description": "Период агрегации (по умолчанию month)"},
            "moving_avg_window": {"type": "integer", "description": "Окно скользящего среднего (по умолчанию 3)"},
        },
        "required": ["table_name"],
    },
)
def time_analysis(
    session: Session,
    table_name: str,
    date_column: str = "",
    value_column: str = "",
    period: str = "month",
    moving_avg_window: int = 3,
) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn
    schema = conn.execute(f'DESCRIBE "{table_name}"').fetchall()

    if not date_column:
        date_types = {"date", "timestamp", "timestamptz", "datetime", "timestamp with time zone", "timestamp without time zone"}
        date_cols = [s[0] for s in schema if any(t in s[1].lower() for t in date_types)]
        if not date_cols:
            date_cols = [s[0] for s in schema if "date" in s[0].lower() or "time" in s[0].lower() or "at" in s[0].lower()]
        if not date_cols:
            return "Не удалось автоматически определить колонку с датой. Укажите date_column."
        date_column = date_cols[0]

    if not value_column:
        numeric_types = {"integer", "bigint", "float", "double", "decimal", "numeric", "real"}
        numeric_cols = [s[0] for s in schema if any(t in s[1].lower() for t in numeric_types) and s[0] != date_column]
        if not numeric_cols:
            return "Не удалось автоматически определить числовую колонку. Укажите value_column."
        value_column = numeric_cols[0]

    period_map = {"day": "day", "week": "week", "month": "month", "quarter": "quarter", "year": "year"}
    trunc = period_map.get(period, "month")

    out = [f"Анализ временного ряда: {table_name}", f"Дата: {date_column}, Значение: {value_column}, Период: {period}", ""]

    try:
        ts_sql = (
            f'SELECT DATE_TRUNC(\'{trunc}\', "{date_column}") as period_start, '
            f'COUNT(*) as record_count, '
            f'SUM("{value_column}") as total, '
            f'AVG("{value_column}") as avg_val, '
            f'MIN("{value_column}") as min_val, '
            f'MAX("{value_column}") as max_val '
            f'FROM "{table_name}" '
            f'WHERE "{date_column}" IS NOT NULL AND "{value_column}" IS NOT NULL '
            f'GROUP BY period_start ORDER BY period_start'
        )
        ts_result = conn.execute(ts_sql)
        ts_cols = [d[0] for d in ts_result.description]
        ts_rows = ts_result.fetchall()
    except Exception as e:
        return f"Ошибка запроса: {e}"

    if len(ts_rows) < 2:
        return "Недостаточно данных для анализа временного ряда (нужно минимум 2 периода)."

    out.append(f"Данные по периодам ({len(ts_rows)} периодов):")
    out.append(format_table(ts_cols, ts_rows[:50]))
    out.append("")

    if len(ts_rows) >= 3:
        try:
            trend_sql = (
                f'SELECT REGR_SLOPE(CAST(ROW_NUMBER() OVER () AS DOUBLE), CAST("{value_column}" AS DOUBLE)) as slope, '
                f'REGR_INTERCEPT(CAST(ROW_NUMBER() OVER () AS DOUBLE), CAST("{value_column}" AS DOUBLE)) as intercept '
                f'FROM (SELECT DATE_TRUNC(\'{trunc}\', "{date_column}") as p, AVG("{value_column}") as v '
                f'FROM "{table_name}" WHERE "{date_column}" IS NOT NULL AND "{value_column}" IS NOT NULL '
                f'GROUP BY p) ORDER BY p'
            )
            trend = conn.execute(trend_sql).fetchone()
        except Exception:
            try:
                first_val = ts_rows[0][3]
                last_val = ts_rows[-1][3]
                if first_val and last_val and first_val != 0:
                    total_change = ((last_val - first_val) / abs(first_val)) * 100
                    trend_dir = "рост" if total_change > 0 else "падение" if total_change < 0 else "стабильно"
                    out.append(f"Общее изменение: {trend_dir} на {abs(round(total_change, 1))}%")
            except Exception:
                pass
            trend = None

        if trend and trend[0] is not None:
            slope = trend[0]
            direction = "восходящий" if slope > 0 else "нисходящий" if slope < 0 else "горизонтальный"
            out.append(f"Тренд: {direction} (slope={round(slope, 4)})")

    if len(ts_rows) >= 2:
        out.append("")
        out.append("Изменение по периодам:")
        prev = None
        for r in ts_rows[:30]:
            period_start = r[0]
            total = r[2]
            avg_v = r[3]
            change_str = ""
            if prev is not None:
                try:
                    if prev != 0:
                        change = ((avg_v - prev) / abs(prev)) * 100
                        arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
                        change_str = f" {arrow} {abs(round(change, 1))}%"
                except Exception:
                    pass
            out.append(f"  {period_start}: avg={round(avg_v, 2)}, total={round(total, 2)}{change_str}")
            prev = avg_v

    if len(ts_rows) >= moving_avg_window * 2:
        try:
            ma_sql = (
                f'SELECT period_start, avg_val, '
                f'AVG(avg_val) OVER (ORDER BY period_start ROWS BETWEEN {moving_avg_window - 1} PRECEDING AND CURRENT ROW) as moving_avg '
                f'FROM (SELECT DATE_TRUNC(\'{trunc}\', "{date_column}") as period_start, '
                f'AVG("{value_column}") as avg_val FROM "{table_name}" '
                f'WHERE "{date_column}" IS NOT NULL AND "{value_column}" IS NOT NULL '
                f'GROUP BY period_start) ORDER BY period_start'
            )
            ma_result = conn.execute(ma_sql).fetchall()
            out.append("")
            out.append(f"Скользящее среднее (окно={moving_avg_window}):")
            for period_start, avg_v, ma in ma_result[-15:]:
                out.append(f"  {period_start}: {round(avg_v, 2)} (MA: {round(ma, 2)})")
        except Exception:
            pass

    try:
        range_sql = (
            f'SELECT MIN("{date_column}"), MAX("{date_column}") FROM "{table_name}" WHERE "{date_column}" IS NOT NULL'
        )
        date_range = conn.execute(range_sql).fetchone()
        out.append("")
        out.append(f"Период данных: {date_range[0]} — {date_range[1]}")
    except Exception:
        pass

    return "\n".join(out)

from __future__ import annotations

from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="segment_data",
    description="Сегментация данных: разбивает числовые колонки на квантильные группы (квинтили, децилы, кастомные бакеты), добавляет колонку сегмента. Поддерживает RFM-анализ (recency, frequency, monetary).",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "column": {"type": "string", "description": "Числовая колонка для сегментации"},
            "method": {"type": "string", "enum": ["quintile", "decile", "quartile", "tertile", "custom"], "description": "Метод: quintile (5 групп), decile (10), quartile (4), tertile (3), custom (свои границы)"},
            "custom_bounds": {"type": "string", "description": "Границы бакетов через запятую (для method=custom, например: 0,100,500,1000)"},
            "rfm_mode": {"type": "boolean", "description": "Включить RFM-анализ (нужны date_column, id_column, amount_column)"},
            "date_column": {"type": "string", "description": "Колонка с датой (для RFM recency)"},
            "id_column": {"type": "string", "description": "Колонка с ID клиента (для RFM frequency)"},
            "amount_column": {"type": "string", "description": "Колонка с суммой (для RFM monetary)"},
        },
        "required": ["table_name", "column"],
    },
)
def segment_data(
    session: Session,
    table_name: str,
    column: str,
    method: str = "quintile",
    custom_bounds: str = "",
    rfm_mode: bool = False,
    date_column: str = "",
    id_column: str = "",
    amount_column: str = "",
) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn

    if rfm_mode and date_column and id_column and amount_column:
        return _rfm_analysis(conn, table_name, date_column, id_column, amount_column)

    ntile_map = {"quintile": 5, "decile": 10, "quartile": 4, "tertile": 3}
    n_tiles = ntile_map.get(method, 5)

    if method == "custom" and custom_bounds.strip():
        bounds = [float(b.strip()) for b in custom_bounds.split(",")]
        if len(bounds) < 2:
            return "Нужно минимум 2 границы для custom бакетов."

        conditions = []
        for i in range(len(bounds) - 1):
            label = f"[{bounds[i]}-{bounds[i+1]})"
            conditions.append(f"WHEN \"{column}\" >= {bounds[i]} AND \"{column}\" < {bounds[i+1]} THEN '{label}'")
        conditions.append(f"ELSE '[{bounds[-1]}+]'")
        case_sql = "CASE " + " ".join(conditions) + " END"

        try:
            sql = f'SELECT {case_sql} as segment, COUNT(*) as cnt, AVG("{column}") as avg_val FROM "{table_name}" WHERE "{column}" IS NOT NULL GROUP BY segment ORDER BY segment'
            result = conn.execute(sql)
            columns = [d[0] for d in result.description]
            rows = result.fetchall()
        except Exception as e:
            return f"Ошибка: {e}"
    else:
        try:
            sql = f'SELECT NTILE({n_tiles}) OVER (ORDER BY "{column}") as segment, COUNT(*) as cnt, AVG("{column}") as avg_val, MIN("{column}") as min_val, MAX("{column}") as max_val FROM "{table_name}" WHERE "{column}" IS NOT NULL GROUP BY segment ORDER BY segment'
            result = conn.execute(sql)
            columns = [d[0] for d in result.description]
            rows = result.fetchall()
        except Exception:
            try:
                quantiles = [round(i / n_tiles, 4) for i in range(n_tiles + 1)]
                pct_sql = ", ".join(
                    f'PERCENTILE_CONT({q}) WITHIN GROUP (ORDER BY "{column}") as p{i}'
                    for i, q in enumerate(quantiles)
                )
                bounds_row = conn.execute(f'SELECT {pct_sql} FROM "{table_name}" WHERE "{column}" IS NOT NULL').fetchone()

                rows = []
                for i in range(n_tiles):
                    lo = bounds_row[i] if bounds_row else 0
                    hi = bounds_row[i + 1] if bounds_row else 0
                    cnt = conn.execute(
                        f'SELECT COUNT(*) FROM "{table_name}" WHERE "{column}" >= {lo} AND "{column}" {"<=" if i == n_tiles - 1 else "<"} {hi}'
                    ).fetchone()[0]
                    avg_val = conn.execute(
                        f'SELECT AVG("{column}") FROM "{table_name}" WHERE "{column}" >= {lo} AND "{column}" {"<=" if i == n_tiles - 1 else "<"} {hi}'
                    ).fetchone()[0]
                    rows.append((f"Группа {i+1} [{round(lo,2)}-{round(hi,2)}]", cnt, round(avg_val, 2) if avg_val else 0, round(lo, 2), round(hi, 2)))
                columns = ["segment", "cnt", "avg_val", "min_val", "max_val"]
            except Exception as e:
                return f"Ошибка сегментации: {e}"

    total = sum(r[1] for r in rows) if rows else 0
    out = [
        f"Сегментация {column} ({method}, {n_tiles} групп): {table_name}",
        f"Всего строк: {total}",
        "",
        format_table(columns, rows),
    ]

    if rows and total > 0:
        out.append("")
        out.append("Распределение по сегментам:")
        for r in rows[:10]:
            label = r[0]
            cnt = r[1]
            pct = round(cnt / total * 100, 1)
            bar = "█" * int(pct / 2)
            out.append(f"  {str(label):>25} {cnt:>6} ({pct:>5}%) {bar}")

    return "\n".join(out)


def _rfm_analysis(conn, table_name: str, date_column: str, id_column: str, amount_column: str) -> str:
    try:
        max_date = conn.execute(f'SELECT MAX("{date_column}") FROM "{table_name}"').fetchone()[0]
        if not max_date:
            return "Не удалось определить максимальную дату."

        sql = f'''
        SELECT 
            "{id_column}" as client_id,
            DATEDIFF('day', MAX("{date_column}"), DATE '{max_date}') as recency_days,
            COUNT(*) as frequency,
            SUM("{amount_column}") as monetary
        FROM "{table_name}"
        WHERE "{date_column}" IS NOT NULL AND "{id_column}" IS NOT NULL AND "{amount_column}" IS NOT NULL
        GROUP BY "{id_column}"
        ORDER BY monetary DESC
        LIMIT 200
        '''
        result = conn.execute(sql)
        columns = [d[0] for d in result.description]
        rows = result.fetchall()

        if not rows:
            return "Нет данных для RFM-анализа."

        for i, row in enumerate(rows):
            r_score = 5 if row[1] <= 30 else 4 if row[1] <= 90 else 3 if row[1] <= 180 else 2 if row[1] <= 365 else 1
            f_score = 5 if row[2] >= 10 else 4 if row[2] >= 5 else 3 if row[2] >= 3 else 2 if row[2] >= 2 else 1
            m_score = 5 if row[3] and row[3] >= 10000 else 4 if row[3] and row[3] >= 5000 else 3 if row[3] and row[3] >= 1000 else 2 if row[3] and row[3] >= 100 else 1
            rfm = r_score * 100 + f_score * 10 + m_score

        out = [
            f"RFM-анализ: {table_name}",
            f"Дата отсчёта: {max_date}",
            f"Клиентов в анализе: {len(rows)}",
            "",
            "Топ клиентов по RFM-скорингу:",
            format_table(columns, rows[:20]),
            "",
            "Оценка R (Recency): 5=≤30дн, 4=≤90дн, 3=≤180дн, 2=≤365дн, 1=>365дн",
            "Оценка F (Frequency): 5=≥10, 4=≥5, 3=≥3, 2=≥2, 1=1",
            "Оценка M (Monetary): 5=≥10000, 4=≥5000, 3=≥1000, 2=≥100, 1=<100",
        ]
        return "\n".join(out)
    except Exception as e:
        return f"Ошибка RFM-анализа: {e}"

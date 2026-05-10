from __future__ import annotations

from app.session import Session
from .registry import register_tool


@register_tool(
    name="find_duplicates",
    description="Поиск дубликатов в таблице. Поддерживает: точные дубликаты (по всем или указанным колонкам), почти-дубликаты (fuzzy matching по Levenshtein-расстоянию).",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Имя таблицы",
            },
            "columns": {
                "type": "string",
                "description": "Колонки для проверки дубликатов через запятую (необязательно, по умолчанию все)",
            },
            "mode": {
                "type": "string",
                "enum": ["exact", "fuzzy"],
                "description": "Режим поиска: exact — точные дубли, fuzzy — похожие строки (по Levenshtein)",
            },
            "fuzzy_threshold": {
                "type": "number",
                "description": "Порог похожести для fuzzy режима (0.0-1.0, по умолчанию 0.8)",
            },
        },
        "required": ["table_name"],
    },
)
def find_duplicates(
    session: Session,
    table_name: str,
    columns: str = "",
    mode: str = "exact",
    fuzzy_threshold: float = 0.8,
) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn

    if columns.strip():
        cols = [c.strip() for c in columns.split(",")]
    else:
        schema = conn.execute(f'DESCRIBE "{table_name}"').fetchall()
        cols = [s[0] for s in schema]

    if mode == "exact":
        cols_sql = ", ".join(f'"{c}"' for c in cols)
        dup_sql = (
            f'SELECT {cols_sql}, COUNT(*) as duplicate_count '
            f'FROM "{table_name}" '
            f"GROUP BY {cols_sql} "
            f"HAVING COUNT(*) > 1 "
            f"ORDER BY duplicate_count DESC"
        )
        try:
            result = conn.execute(dup_sql)
            res_cols = [d[0] for d in result.description]
            rows = result.fetchmany(100)
        except Exception as e:
            return f"SQL ошибка: {e}"

        if not rows:
            return "Точные дубликаты не найдены."

        from .registry import format_table

        total_dup_groups = len(rows)
        total_dup_rows = sum(r[-1] for r in rows)
        return (
            f"Найдено {total_dup_groups} групп дубликатов "
            f"({total_dup_rows} повторяющихся строк):\n\n"
            f"{format_table(res_cols, rows)}"
        )

    elif mode == "fuzzy":
        str_cols = [c for c in cols if _is_string_col(conn, table_name, c)]
        if not str_cols:
            return "Для fuzzy поиска нужны строковые колонки."

        cols_sql = ", ".join(f'"{c}"' for c in str_cols)
        sample_sql = f'SELECT rowid, {cols_sql} FROM "{table_name}" LIMIT 500'
        try:
            rows = conn.execute(sample_sql).fetchall()
        except Exception as e:
            return f"SQL ошибка: {e}"

        if len(rows) < 2:
            return "Недостаточно строк для fuzzy поиска."

        try:
            from rapidfuzz import fuzz as rfuzz
        except ImportError:
            return "Для fuzzy поиска нужен пакет rapidfuzz. Установите: pip install rapidfuzz"

        pairs = []
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                scores = []
                for ci in range(1, len(str_cols) + 1):
                    v1 = str(rows[i][ci]) if rows[i][ci] else ""
                    v2 = str(rows[j][ci]) if rows[j][ci] else ""
                    if v1 and v2:
                        scores.append(rfuzz.ratio(v1, v2) / 100.0)
                if scores:
                    avg_score = sum(scores) / len(scores)
                    if avg_score >= fuzzy_threshold:
                        pairs.append((rows[i], rows[j], round(avg_score, 2)))

        if not pairs:
            return f"Fuzzy-дубликаты с порогом {fuzzy_threshold} не найдены."

        out_lines = [f"Найдено {len(pairs)} пар похожих строк (порог >= {fuzzy_threshold}):\n"]
        for idx, (r1, r2, score) in enumerate(pairs[:20], 1):
            out_lines.append(f"  Пара {idx} (схожесть: {score}):")
            out_lines.append(f"    Строка {r1[0]}: {r1[1:]}")
            out_lines.append(f"    Строка {r2[0]}: {r2[1:]}")
            out_lines.append("")

        if len(pairs) > 20:
            out_lines.append(f"  ... и ещё {len(pairs) - 20} пар")

        return "\n".join(out_lines)

    return f"Неизвестный режим: {mode}. Используйте 'exact' или 'fuzzy'."


def _is_string_col(conn, table_name: str, col: str) -> bool:
    try:
        tp = conn.execute(f'DESCRIBE "{table_name}"').fetchall()
        for name, dtype, *_ in tp:
            if name == col:
                return any(t in dtype.lower() for t in ["varchar", "text", "char", "string", "blob"])
        return False
    except Exception:
        return False

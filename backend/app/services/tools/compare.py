from __future__ import annotations

from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="compare_tables",
    description="Сравнение двух таблиц: общие строки, уникальные для каждой, расхождения по значениям, A-B анализ. Один файл как справочник, другой как фактические данные. Поиск различий и совпадений.",
    parameters={
        "type": "object",
        "properties": {
            "table_a": {"type": "string", "description": "Первая таблица (или справочник)"},
            "table_b": {"type": "string", "description": "Вторая таблица (или фактические данные)"},
            "key_columns": {"type": "string", "description": "Ключевые колонки для сопоставления через запятую"},
            "compare_columns": {"type": "string", "description": "Колонки для сравнения значений через запятую (необязательно, по умолчанию все общие)"},
            "mode": {"type": "string", "enum": ["full", "missing_only", "differences_only"], "description": "Режим: full — полный отчёт, missing_only — только отсутствующие строки, differences_only — только расхождения"},
        },
        "required": ["table_a", "table_b", "key_columns"],
    },
)
def compare_tables(
    session: Session,
    table_a: str,
    table_b: str,
    key_columns: str,
    compare_columns: str = "",
    mode: str = "full",
) -> str:
    available = {fi.table_name for fi in session.files.values()}
    if table_a not in available:
        return f"Таблица '{table_a}' не найдена. Доступные: {sorted(available)}"
    if table_b not in available:
        return f"Таблица '{table_b}' не найдена. Доступные: {sorted(available)}"

    conn = session.conn
    keys = [k.strip() for k in key_columns.split(",")]
    join_cond = " AND ".join(f'a."{k}" = b."{k}"' for k in keys)

    schema_a = conn.execute(f'DESCRIBE "{table_a}"').fetchall()
    schema_b = conn.execute(f'DESCRIBE "{table_b}"').fetchall()
    cols_a = {s[0] for s in schema_a}
    cols_b = {s[0] for s in schema_b}

    common_cols = cols_a & cols_b - set(keys)
    if compare_columns.strip():
        common_cols = {c.strip() for c in compare_columns.split(",")} & common_cols

    results = []

    count_a = conn.execute(f'SELECT COUNT(*) FROM "{table_a}"').fetchone()[0]
    count_b = conn.execute(f'SELECT COUNT(*) FROM "{table_b}"').fetchone()[0]
    results.append(f"Сравнение: {table_a} ({count_a:,} строк) ↔ {table_b} ({count_b:,} строк)")
    results.append(f"Ключ: {', '.join(keys)}")
    results.append("")

    if mode in ("full", "missing_only"):
        only_a = conn.execute(
            f'SELECT COUNT(*) FROM "{table_a}" a WHERE NOT EXISTS '
            f'(SELECT 1 FROM "{table_b}" b WHERE {join_cond})'
        ).fetchone()[0]

        only_b = conn.execute(
            f'SELECT COUNT(*) FROM "{table_b}" b WHERE NOT EXISTS '
            f'(SELECT 1 FROM "{table_a}" a WHERE {join_cond})'
        ).fetchone()[0]

        both = conn.execute(
            f'SELECT COUNT(*) FROM "{table_a}" a JOIN "{table_b}" b ON {join_cond}'
        ).fetchone()[0]

        results.append("Совпадение по ключу:")
        results.append(f"  Общих строк: {both:,}")
        results.append(f"  Только в {table_a}: {only_a:,}")
        results.append(f"  Только в {table_b}: {only_b:,}")

        keys_select = ", ".join(f'"{k}"' for k in keys)
        if only_a > 0:
            sample_a = conn.execute(
                f'SELECT {keys_select} FROM "{table_a}" a '
                f'WHERE NOT EXISTS (SELECT 1 FROM "{table_b}" b WHERE {join_cond}) LIMIT 10'
            ).fetchall()
            results.append(f"\nПримеры строк только в {table_a}:")
            for r in sample_a:
                results.append(f"  {r}")

        if only_b > 0:
            sample_b = conn.execute(
                f'SELECT {keys_select} FROM "{table_b}" b '
                f'WHERE NOT EXISTS (SELECT 1 FROM "{table_a}" a WHERE {join_cond}) LIMIT 10'
            ).fetchall()
            results.append(f"\nПримеры строк только в {table_b}:")
            for r in sample_b:
                results.append(f"  {r}")

        results.append("")

    if common_cols and mode in ("full", "differences_only"):
        diff_cols = []
        for col in common_cols:
            try:
                diff_count = conn.execute(
                    f'SELECT COUNT(*) FROM "{table_a}" a JOIN "{table_b}" b ON {join_cond} '
                    f'WHERE a."{col}" != b."{col}" OR (a."{col}" IS NULL) != (b."{col}" IS NULL)'
                ).fetchone()[0]
                if diff_count > 0:
                    diff_cols.append((col, diff_count))
            except Exception:
                pass

        if diff_cols:
            results.append("Расхождения в значениях:")
            for col, cnt in diff_cols:
                pct = round(cnt / both * 100, 1) if both else 0
                results.append(f"  {col}: {cnt} различий ({pct}%)")

                sample = conn.execute(
                    f'SELECT a."{col}" as val_a, b."{col}" as val_b '
                    f'FROM "{table_a}" a JOIN "{table_b}" b ON {join_cond} '
                    f'WHERE a."{col}" != b."{col}" OR (a."{col}" IS NULL) != (b."{col}" IS NULL) LIMIT 5'
                ).fetchall()
                for va, vb in sample:
                    results.append(f"    {table_a}: {va} → {table_b}: {vb}")
        elif mode != "missing_only":
            results.append("Расхождения в значениях не найдены — все общие колонки совпадают.")

    return "\n".join(results)

from __future__ import annotations

from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="correlation_analysis",
    description="Корреляционный анализ: матрица корреляций Пирсона между числовыми колонками. Выявляет скрытые связи между переменными. Показывает только значимые корреляции (|r| > 0.3) с интерпретацией силы связи.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "columns": {"type": "string", "description": "Числовые колонки через запятую (необязательно, по умолчанию все числовые)"},
            "method": {"type": "string", "enum": ["pearson", "spearman"], "description": "Метод корреляции: pearson (линейная связь, по умолчанию), spearman (ранговая, для нелинейных связей)"},
            "min_strength": {"type": "number", "description": "Минимальная сила корреляции для вывода (0-1, по умолчанию 0.3)"},
        },
        "required": ["table_name"],
    },
)
def correlation_analysis(
    session: Session,
    table_name: str,
    columns: str = "",
    method: str = "pearson",
    min_strength: float = 0.3,
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

    if len(numeric_cols) < 2:
        return "Нужно минимум 2 числовые колонки для корреляционного анализа."

    func = "CORR" if method == "pearson" else "CORR"

    if method == "spearman":
        for col in numeric_cols:
            conn.execute(
                f'CREATE TEMP SEQUENCE IF NOT EXISTS _rank_seq_{col}; '
                f'CREATE TEMP TABLE IF NOT EXISTS _ranks_{col} AS '
                f'SELECT "{col}", ROW_NUMBER() OVER (ORDER BY "{col}") as _rank '
                f'FROM (SELECT DISTINCT "{col}" FROM "{table_name}" WHERE "{col}" IS NOT NULL ORDER BY "{col}")'
            )

    pairs = []
    for i, col_a in enumerate(numeric_cols):
        for col_b in numeric_cols[i + 1:]:
            if method == "spearman":
                sql = (
                    f'SELECT CORR(a._rank, b._rank) FROM _ranks_{col_a} a '
                    f'JOIN _ranks_{col_b} b ON a."{col_a}" IS NOT NULL AND b."{col_b}" IS NOT NULL'
                )
            else:
                sql = f'SELECT CORR("{col_a}", "{col_b}") FROM "{table_name}" WHERE "{col_a}" IS NOT NULL AND "{col_b}" IS NOT NULL'
            try:
                r = conn.execute(sql).fetchone()[0]
                if r is not None:
                    pairs.append((col_a, col_b, round(r, 4)))
            except Exception:
                pass

    if method == "spearman":
        for col in numeric_cols:
            try:
                conn.execute(f'DROP TABLE IF EXISTS _ranks_{col}')
            except Exception:
                pass

    significant = [(a, b, r) for a, b, r in pairs if abs(r) >= min_strength]
    significant.sort(key=lambda x: -abs(x[2]))

    def interpret(r: float) -> str:
        ar = abs(r)
        direction = "положительная" if r > 0 else "отрицательная"
        if ar >= 0.9:
            return f"очень сильная {direction}"
        elif ar >= 0.7:
            return f"сильная {direction}"
        elif ar >= 0.5:
            return f"умеренная {direction}"
        elif ar >= 0.3:
            return f"слабая {direction}"
        return f"очень слабая {direction}"

    out = [f"Корреляционный анализ ({method}): {table_name}", ""]

    if not significant:
        out.append(f"Значимых корреляций (|r| >= {min_strength}) не найдено.")
        if pairs:
            out.append("")
            out.append("Все корреляции:")
            for a, b, r in sorted(pairs, key=lambda x: -abs(x[2]))[:20]:
                out.append(f"  {a} ↔ {b}: r = {r:+.4f} ({interpret(r)})")
        return "\n".join(out)

    out.append(f"Значимые корреляции (|r| >= {min_strength}):")
    out.append("")
    for a, b, r in significant:
        out.append(f"  **{a} ↔ {b}**: r = {r:+.4f}")
        out.append(f"    Интерпретация: {interpret(r)} связь")
        if abs(r) >= 0.7:
            out.append(f"    Вывод: {a} и {b} {'сильно связаны' if r > 0 else 'сильно обратно связаны'}. Изменение одного предсказывает изменение другого.")
        elif abs(r) >= 0.5:
            out.append(f"    Вывод: {a} и {b} умеренно связаны. Есть паттерн, но возможны исключения.")
        out.append("")

    matrix_cols = numeric_cols[:15]
    if len(matrix_cols) >= 2:
        out.append("Матрица корреляций:")
        header = "        " + "  ".join(c[:8].ljust(8) for c in matrix_cols)
        out.append(header)
        for ca in matrix_cols:
            row_vals = []
            for cb in matrix_cols:
                if ca == cb:
                    row_vals.append("  1.00  ")
                else:
                    found = [r for a, b, r in pairs if (a == ca and b == cb) or (a == cb and b == ca)]
                    if found:
                        row_vals.append(f" {found[0]:+.2f}  ")
                    else:
                        row_vals.append("   -    ")
            out.append(ca[:8].ljust(8) + "  ".join(row_vals))

    return "\n".join(out)

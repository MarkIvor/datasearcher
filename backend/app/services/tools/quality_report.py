from __future__ import annotations

from app.session import Session
from .registry import register_tool


@register_tool(
    name="data_quality_report",
    description="Комплексный отчёт о качестве данных: полнота (null-проценты), консистентность (дубликаты ключей, формат данных), типы данных, рекомендуемые исправления. Всё в одном вызове вместо 3-4 отдельных инструментов.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "key_columns": {"type": "string", "description": "Ключевые колонки для проверки уникальности через запятую (необязательно)"},
        },
        "required": ["table_name"],
    },
)
def data_quality_report(session: Session, table_name: str, key_columns: str = "") -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn
    schema = conn.execute(f'DESCRIBE "{table_name}"').fetchall()
    count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]

    if count == 0:
        return f"Таблица {table_name} пуста."

    out = [
        f"# Отчёт о качестве данных: {table_name}",
        f"Строк: {count:,}, Колонок: {len(schema)}",
        "",
    ]

    total_cells = count * len(schema)
    null_cells = 0
    issues = []
    good_cols = 0

    out.append("## Полнота данных")
    completeness_lines = []
    for row in schema:
        col_name, col_type = row[0], row[1]
        null_count = conn.execute(
            f'SELECT COUNT(*) FROM "{table_name}" WHERE "{col_name}" IS NULL'
        ).fetchone()[0]
        null_pct = round(null_count / count * 100, 1) if count else 0
        null_cells += null_count

        if null_pct > 0:
            severity = "КРИТИЧНО" if null_pct > 50 else "ПРЕДУПРЕЖДЕНИЕ" if null_pct > 10 else "ОК"
            completeness_lines.append(f"  - {col_name} [{col_type}]: {null_pct}% null ({null_count:,}) — {severity}")
            if null_pct > 50:
                issues.append(f"Колонка {col_name} имеет {null_pct}% пропусков — рассмотрите удаление или заполнение")
            elif null_pct > 10:
                issues.append(f"Колонка {col_name} имеет {null_pct}% пропусков — проверьте влияние на аналитику")
        else:
            good_cols += 1

    if completeness_lines:
        out.extend(completeness_lines)
    out.append(f"\nИтого: {good_cols}/{len(schema)} колонок без пропусков")
    overall_completeness = round((1 - null_cells / total_cells) * 100, 1) if total_cells else 0
    out.append(f"Общая полнота: {overall_completeness}%")

    out.append("")
    out.append("## Уникальность")
    total_dup_rows = 0
    for row in schema:
        col_name = row[0]
        distinct = conn.execute(
            f'SELECT COUNT(DISTINCT "{col_name}") FROM "{table_name}" WHERE "{col_name}" IS NOT NULL'
        ).fetchone()[0]
        dup_count = count - distinct - conn.execute(
            f'SELECT COUNT(*) FROM "{table_name}" WHERE "{col_name}" IS NULL'
        ).fetchone()[0]
        if dup_count > 0:
            out.append(f"  - {col_name}: {dup_count:,} повторяющихся значений ({distinct:,} уникальных)")

    if key_columns.strip():
        keys = [k.strip() for k in key_columns.split(",")]
        keys_sql = ", ".join(f'"{k}"' for k in keys)
        dup_keys = conn.execute(
            f'SELECT COUNT(*) FROM (SELECT {keys_sql}, COUNT(*) as c FROM "{table_name}" GROUP BY {keys_sql} HAVING c > 1)'
        ).fetchone()[0]
        if dup_keys > 0:
            out.append(f"  - Дубликаты по ключу ({', '.join(keys)}): {dup_keys:,} групп")
            issues.append(f"Найдено {dup_keys} групп дубликатов по ключу ({', '.join(keys)})")
        else:
            out.append(f"  - Ключ ({', '.join(keys)}): уникален ✓")

    out.append("")
    out.append("## Консистентность типов")
    for row in schema:
        col_name, col_type = row[0], row[1]
        col_type_lower = col_type.lower()
        if any(t in col_type_lower for t in ["varchar", "text", "char", "string"]):
            empty_count = conn.execute(
                f'SELECT COUNT(*) FROM "{table_name}" WHERE "{col_name}" = \'\''
            ).fetchone()[0]
            if empty_count > 0:
                out.append(f"  - {col_name}: {empty_count:,} пустых строк (не NULL)")

            sample = conn.execute(
                f'SELECT DISTINCT "{col_name}" FROM "{table_name}" WHERE "{col_name}" IS NOT NULL LIMIT 5'
            ).fetchall()
            numeric_like = 0
            for (val,) in sample:
                if val and str(val).replace(".", "").replace("-", "").replace(",", "").isdigit():
                    numeric_like += 1
            if numeric_like == len(sample) and len(sample) > 0:
                out.append(f"  - {col_name}: строковый тип, но значения похожи на числа — рассмотрите CAST")
                issues.append(f"{col_name}: возможно числовая колонка хранится как строка")

    out.append("")
    out.append("## Рекомендации")
    if not issues:
        out.append("Данные выглядят хорошо! Серьёзных проблем не обнаружено.")
    else:
        for i, issue in enumerate(issues, 1):
            out.append(f"{i}. {issue}")

    score = max(0, min(100, overall_completeness - len(issues) * 5))
    out.append(f"\nОбщая оценка качества: {score}/100")

    return "\n".join(out)

from __future__ import annotations

import re

from app.session import Session
from .registry import register_tool


@register_tool(
    name="detect_patterns",
    description="Распознавание паттернов в текстовых колонках: email, телефон, URL, ИНН, дата-форматы, числа в строках, повторяющиеся шаблоны. Показывает найденные паттерны и их частоту.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "columns": {"type": "string", "description": "Колонки для анализа через запятую (необязательно, все текстовые)"},
        },
        "required": ["table_name"],
    },
)
def detect_patterns(session: Session, table_name: str, columns: str = "") -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn
    schema = conn.execute(f'DESCRIBE "{table_name}"').fetchall()
    string_types = {"varchar", "text", "char", "string"}

    if columns.strip():
        text_cols = [c.strip() for c in columns.split(",")]
    else:
        text_cols = [s[0] for s in schema if any(t in s[1].lower() for t in string_types)]

    if not text_cols:
        return "Текстовые колонки не найдены."

    pattern_defs = {
        "Email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        "Телефон": r'(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
        "URL": r'https?://[^\s<>"{}|\\^`\[\]]+',
        "ИНН": r'\b\d{10,12}\b',
        "Дата (DD.MM.YYYY)": r'\b\d{1,2}\.\d{1,2}\.\d{2,4}\b',
        "Дата (YYYY-MM-DD)": r'\b\d{4}-\d{2}-\d{2}\b',
        "IPv4": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        "GUID/UUID": r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',
        "Число в строке": r'^-?\d+[\.,]?\d*$',
        "Шаблон кода": r'^[A-Z]{2,5}-\d{3,6}$',
    }

    out = [f"# Паттерны в данных: {table_name}", ""]

    total_count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]

    for col in text_cols:
        out.append(f"## {col}")

        try:
            sample = conn.execute(
                f'SELECT "{col}" FROM "{table_name}" '
                f'WHERE "{col}" IS NOT NULL LIMIT 200'
            ).fetchall()
        except Exception:
            continue

        if not sample:
            out.append("  Пустая колонка")
            out.append("")
            continue

        null_count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}" WHERE "{col}" IS NULL').fetchone()[0]
        distinct = conn.execute(f'SELECT COUNT(DISTINCT "{col}") FROM "{table_name}" WHERE "{col}" IS NOT NULL').fetchone()[0]
        out.append(f"  Уникальных: {distinct}, Пропуски: {null_count} ({round(null_count/total_count*100,1) if total_count else 0}%)")

        found_patterns = {}
        for pattern_name, regex in pattern_defs.items():
            matches = 0
            examples = []
            for (val,) in sample:
                if val and re.search(regex, str(val)):
                    matches += 1
                    if len(examples) < 3:
                        examples.append(str(val)[:50])
            if matches > 0:
                found_patterns[pattern_name] = (matches, examples)

        if found_patterns:
            for pname, (cnt, examples) in found_patterns.items():
                pct = round(cnt / len(sample) * 100, 1)
                out.append(f"  **{pname}**: найден в {cnt} строках ({pct}%)")
                for ex in examples:
                    out.append(f"    → `{ex}`")
        else:
            out.append("  Стандартные паттерны не обнаружены")

            all_vals = [str(r[0]) for r in sample if r[0]]
            if all_vals:
                lengths = [len(v) for v in all_vals]
                avg_len = round(sum(lengths) / len(lengths), 1)
                min_len, max_len = min(lengths), max(lengths)
                out.append(f"  Длина: мин={min_len}, макс={max_len}, средняя={avg_len}")

                has_upper = sum(1 for v in all_vals if any(c.isupper() for c in v))
                has_lower = sum(1 for v in all_vals if any(c.islower() for c in v))
                has_digits = sum(1 for v in all_vals if any(c.isdigit() for c in v))
                has_special = sum(1 for v in all_vals if any(not c.isalnum() and c != ' ' for c in v))
                out.append(f"  Состав: верхний={has_upper}, нижний={has_lower}, цифры={has_digits}, спецсимволы={has_special}")

        out.append("")

    return "\n".join(out)

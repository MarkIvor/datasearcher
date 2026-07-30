from __future__ import annotations

import re
from typing import Any

from ..config import settings
from .knowledge_base import get_kb

_PII_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    ("email", "Email", re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
    ("phone", "Телефон", re.compile(
        r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")),
    ("inn", "ИНН", re.compile(r"\b\d{10,12}\b")),
    ("snils", "СНИЛС", re.compile(r"\b\d{3}-\d{3}-\d{3}\s?\d{2}\b")),
    ("passport", "Паспорт", re.compile(r"\b\d{2}\s?\d{2}\s?\d{6}\b")),
    ("card", "Банковская карта", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("ip", "IP-адрес", re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
]

_PII_COLUMN_NAMES: dict[str, str] = {
    "email": "email",
    "e_mail": "email",
    "phone": "phone",
    "tel": "phone",
    "mobile": "phone",
    "inn": "inn",
    "snils": "snils",
    "passport": "passport",
    "card_number": "card",
    "card": "card",
    "credit_card": "card",
    "ip_address": "ip",
    "ip": "ip",
    "address": "address",
    "full_name": "name",
    "first_name": "name",
    "last_name": "name",
    "birth_date": "birthdate",
    "birthday": "birthdate",
}


def detect_pii_type(column_name: str, sample_values: list[Any]) -> str:
    """Определить PII-тип колонки по названию и sample-значениям."""
    cn_lower = column_name.lower().replace(" ", "_").replace("-", "_")

    for pattern, pii_type in _PII_COLUMN_NAMES.items():
        if pattern in cn_lower:
            return pii_type

    if sample_values:
        for val in sample_values[:settings.pii_scan_rows]:
            if val is None:
                continue
            s = str(val)
            for pii_type, _, regex in _PII_PATTERNS:
                if regex.search(s):
                    return pii_type

    return ""


def scan_table_for_pii(
    table_name: str,
    columns: list[dict],
    sample_rows: list[tuple],
) -> list[dict]:
    """Сканировать таблицу на PII. Возвращает список колонок с PII-типом."""
    pii_found = []
    for i, col in enumerate(columns):
        col_name = col["name"]
        col_type = (col.get("type") or "").lower()
        if not any(t in col_type for t in ("varchar", "text", "char", "string", "str")):
            continue
        sample_vals = []
        if sample_rows and i < len(sample_rows[0]):
            sample_vals = [row[i] for row in sample_rows]
        pii_type = detect_pii_type(col_name, sample_vals)
        if pii_type:
            pii_found.append({
                "column": col_name,
                "pii_type": pii_type,
            })
            get_kb().upsert_column(
                table_name, col_name,
                pii_type=pii_type,
                is_sensitive=True,
                source="auto_scan",
            )
    return pii_found


def mask_value(value: Any, pii_type: str) -> str:
    """Замаскировать значение по PII-типу."""
    if value is None:
        return ""
    s = str(value)

    if pii_type == "email":
        at = s.find("@")
        if at > 1:
            return s[0] + "***@" + s[at + 1:]
        return "***@" + s

    if pii_type == "phone":
        digits = re.sub(r"\D", "", s)
        if len(digits) >= 4:
            return f"+{digits[0]}({digits[1:4]})***-**-{digits[-2:]}"

    if pii_type == "inn":
        if len(s) >= 4:
            return s[:4] + "******"

    if pii_type in ("snils", "passport"):
        return "***-***-" + s[-2:] if len(s) >= 2 else "***"

    if pii_type == "card":
        return "**** **** **** " + s[-4:] if len(s) >= 4 else "****"

    if pii_type == "ip":
        parts = s.split(".")
        if len(parts) == 4:
            return parts[0] + "." + parts[1] + ".***.***"
        return "***.***.***.***"

    if pii_type in ("name", "address", "birthdate"):
        return "***"

    return s


def mask_row(row: tuple, columns: list[dict], pii_columns: list[dict]) -> tuple:
    """Замаскировать PII-поля в строке.

    pii_columns может содержать ключ 'column' (из scan_table_for_pii)
    или 'column_name' (из KB.get_pii_columns).
    """
    if not pii_columns or not settings.pii_masking:
        return row

    pii_map = {}
    for pc in pii_columns:
        col = pc.get("column") or pc.get("column_name") or ""
        if col:
            pii_map[col] = pc["pii_type"]
    col_names = [c["name"] for c in columns]
    result = list(row)

    for i, col_name in enumerate(col_names):
        if col_name in pii_map and i < len(result):
            result[i] = mask_value(result[i], pii_map[col_name])

    return tuple(result)


def get_pii_columns_for_table(table_name: str) -> list[dict]:
    """Получить PII-колонки таблицы из KB."""
    return get_kb().get_pii_columns(table_name)
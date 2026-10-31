from __future__ import annotations

import json
import os
from typing import Any

from ..config import settings


def extract_marker(text: str, start: str, end: str) -> str:
    s = text.find(start)
    e = text.find(end)
    if s >= 0 and e > s:
        return text[s + len(start):e].strip()
    return ""


def split_markers(text: str, start: str, end: str) -> list[tuple[str, str]]:
    """Возвращает [(маркер_содержимое, остальной_текст_после)]."""
    parts: list[tuple[str, str]] = []
    cursor = 0
    out_text: list[str] = []
    while True:
        s = text.find(start, cursor)
        if s < 0:
            out_text.append(text[cursor:])
            break
        out_text.append(text[cursor:s])
        e = text.find(end, s)
        if e < 0:
            out_text.append(text[s:])
            break
        parts.append((text[s + len(start):e].strip(), ""))
        cursor = e + len(end)
    return parts, "\n".join(p for p in out_text if p)


def collect_charts(text: str) -> tuple[list[dict], str]:
    """Извлекает все __CHART_DATA__ спецификации, возвращает (charts, clean_text)."""
    charts: list[dict] = []
    remaining = text
    while True:
        s = remaining.find("__CHART_DATA__")
        if s < 0:
            break
        e = remaining.find("__END_CHART_DATA__", s)
        if e < 0:
            break
        raw = remaining[s + len("__CHART_DATA__"):e].strip()
        try:
            charts.append(json.loads(raw))
        except json.JSONDecodeError:
            pass
        remaining = remaining[:s] + remaining[e + len("__END_CHART_DATA__"):]
    return charts, remaining.strip()

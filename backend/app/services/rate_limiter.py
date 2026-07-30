from __future__ import annotations

import time
from collections import defaultdict

from ..config import settings

_calls: dict[tuple[str, str], list[float]] = defaultdict(list)

_ML_TOOLS = {
    "cluster_analysis", "predict_trend", "feature_importance",
    "statistical_test", "classify_rows", "semantic_search",
    "auto_insights", "build_dashboard", "data_story",
    "create_public_dashboard", "generate_sql",
}


def _category(tool_name: str) -> str:
    return "ml" if tool_name in _ML_TOOLS else "sql"


def check_rate_limit(tool_name: str, user: str = "") -> tuple[bool, int]:
    """Проверить rate limit для инструмента.

    Returns:
        (allowed, wait_seconds) — True если разрешено, иначе False и сколько ждать.
    """
    if not settings.rate_limit_enabled:
        return True, 0

    cat = _category(tool_name)
    key = (cat, user)
    now = time.time()
    window = 60.0
    limit = settings.rate_limit_ml if cat == "ml" else settings.rate_limit_sql

    _calls[key] = [t for t in _calls[key] if now - t < window]

    if len(_calls[key]) >= limit:
        oldest = min(_calls[key])
        wait = int(window - (now - oldest)) + 1
        return False, max(wait, 1)

    _calls[key].append(now)
    return True, 0


def rate_limit_message(tool_name: str, wait_seconds: int) -> str:
    cat = _category(tool_name)
    limit = settings.rate_limit_ml if cat == "ml" else settings.rate_limit_sql
    return (
        f"⏱️ Rate limit exceeded для {tool_name} "
        f"({limit} {cat}-запросов в минуту). "
        f"Подождите {wait_seconds} сек."
    )
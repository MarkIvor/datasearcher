from __future__ import annotations

from typing import Callable

TOOL_DEFINITIONS: list[dict] = []
TOOL_HANDLERS: dict[str, Callable] = {}


def register_tool(name: str, description: str, parameters: dict):
    def decorator(func):
        TOOL_DEFINITIONS.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                },
            }
        )
        TOOL_HANDLERS[name] = func
        return func

    return decorator


def get_tool_definitions() -> list[dict]:
    return TOOL_DEFINITIONS


def get_tool_handler(name: str) -> Callable | None:
    return TOOL_HANDLERS.get(name)


def format_table(columns: list[str], rows: list[tuple]) -> str:
    if not rows:
        return " | ".join(columns) + "\n(нет данных)"
    col_widths = [
        max(len(str(c)), max(len(str(r[i])) for r in rows) if rows else 0)
        for i, c in enumerate(columns)
    ]
    sep = "-+-".join("-" * w for w in col_widths)
    header = " | ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(columns))
    body = "\n".join(
        " | ".join(str(v).ljust(col_widths[i]) for i, v in enumerate(row))
        for row in rows
    )
    return f"{header}\n{sep}\n{body}"


from .schema import *  # noqa: F401,E402,F403
from .query import *  # noqa: F401,E402,F403
from .profile import *  # noqa: F401,E402,F403
from .classify import *  # noqa: F401,E402,F403
from .duplicates import *  # noqa: F401,E402,F403
from .anomalies import *  # noqa: F401,E402,F403
from .sample import *  # noqa: F401,E402,F403
from .correlation import *  # noqa: F401,E402,F403
from .distribution import *  # noqa: F401,E402,F403
from .cross_tab import *  # noqa: F401,E402,F403
from .pivot import *  # noqa: F401,E402,F403
from .segment import *  # noqa: F401,E402,F403
from .compare import *  # noqa: F401,E402,F403
from .time_analysis import *  # noqa: F401,E402,F403
from .quality_report import *  # noqa: F401,E402,F403
from .smart_summary import *  # noqa: F401,E402,F403
from .generate_sql import *  # noqa: F401,E402,F403
from .visualize import *  # noqa: F401,E402,F403
from .predict import *  # noqa: F401,E402,F403
from .cluster import *  # noqa: F401,E402,F403
from .feature_importance import *  # noqa: F401,E402,F403
from .stat_tests import *  # noqa: F401,E402,F403
from .auto_insights import *  # noqa: F401,E402,F403
from .transform import *  # noqa: F401,E402,F403
from .merge import *  # noqa: F401,E402,F403
from .export import *  # noqa: F401,E402,F403
from .detect_patterns import *  # noqa: F401,E402,F403
from .build_dashboard import *  # noqa: F401,E402,F403
from .data_story import *  # noqa: F401,E402,F403
from .create_public_dashboard import *  # noqa: F401,E402,F403

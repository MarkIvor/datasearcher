from __future__ import annotations

import json
import os
from typing import Any

from ..config import settings

_AGG_BACKEND = None


def _matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    return matplotlib


def render_chart_png(chart_spec: dict, out_dir: str, idx: int = 0) -> str | None:
    """Рендер chart-spec в PNG файл. Возвращает путь или None при неудаче."""
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return None

    chart_type = chart_spec.get("type", "bar")
    title = chart_spec.get("title", f"chart_{idx}")
    data = chart_spec.get("data", [])
    x_key = chart_spec.get("xKey", "")
    y_keys = chart_spec.get("yKeys", [])
    if not data or not y_keys:
        return None

    fig, ax = plt.subplots(figsize=(8, 5), dpi=120)

    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)[:40]
    fname = f"chart_{idx}_{safe_title}.png"
    path = os.path.join(out_dir, fname)

    try:
        if chart_type == "pie":
            labels = [str(d.get(x_key, "")) for d in data]
            values = [_num(d.get(y_keys[0], 0)) for d in data]
            ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
            ax.axis("equal")
        elif chart_type == "histogram":
            values = [_num(d.get(y_keys[0], 0)) for d in data]
            bins_val = [str(d.get(x_key, "")) for d in data]
            ax.bar(range(len(values)), values)
            ax.set_xlabel(x_key)
            ax.set_ylabel(y_keys[0])
        elif chart_type == "scatter":
            xs = [_num(d.get(x_key, 0)) for d in data]
            ys = [_num(d.get(y_keys[0], 0)) for d in data]
            ax.scatter(xs, ys, s=20, alpha=0.6)
            ax.set_xlabel(x_key)
            ax.set_ylabel(y_keys[0])
        elif chart_type == "area":
            xs = [str(d.get(x_key, "")) for d in data]
            for yk in y_keys[:3]:
                ys = [_num(d.get(yk, 0)) for d in data]
                ax.fill_between(range(len(ys)), ys, alpha=0.3, label=yk)
                ax.plot(range(len(ys)), ys, label=yk)
            if len(xs) <= 30:
                ax.set_xticks(range(len(xs)))
                ax.set_xticklabels(xs, rotation=45, ha="right", fontsize=8)
            ax.set_xlabel(x_key)
            ax.legend(fontsize=8)
        elif chart_type == "line":
            xs = [str(d.get(x_key, "")) for d in data]
            for yk in y_keys[:3]:
                ys = [_num(d.get(yk, 0)) for d in data]
                ax.plot(range(len(ys)), ys, marker="o", markersize=3, label=yk)
            if len(xs) <= 30:
                ax.set_xticks(range(len(xs)))
                ax.set_xticklabels(xs, rotation=45, ha="right", fontsize=8)
            ax.set_xlabel(x_key)
            ax.legend(fontsize=8)
        else:  # bar
            xs = [str(d.get(x_key, "")) for d in data]
            if chart_spec.get("horizontal"):
                for yk in y_keys[:1]:
                    ys = [_num(d.get(yk, 0)) for d in data]
                    ax.barh(range(len(ys)), ys)
                    ax.set_yticks(range(len(xs)))
                    ax.set_yticklabels(xs, fontsize=8)
                ax.set_xlabel(y_keys[0])
            else:
                for yk in y_keys[:3]:
                    ys = [_num(d.get(yk, 0)) for d in data]
                    ax.bar([i + 0.2 * y_keys.index(yk) for i in range(len(ys))], ys, width=0.2, label=yk)
                if len(xs) <= 30:
                    ax.set_xticks(range(len(xs)))
                    ax.set_xticklabels(xs, rotation=45, ha="right", fontsize=8)
                ax.set_xlabel(x_key)
                if len(y_keys) > 1:
                    ax.legend(fontsize=8)

        ax.set_title(title, fontsize=12)
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        return path
    except Exception:
        return None
    finally:
        plt.close(fig)


def _num(v: Any) -> float:
    try:
        f = float(v)
        return f
    except (TypeError, ValueError):
        return 0.0

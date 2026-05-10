from __future__ import annotations

import json
import math
from datetime import date, datetime

from app.session import Session
from .registry import format_table, register_tool


def _safe_val(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    try:
        if hasattr(v, "item"):
            return v.item()
    except Exception:
        pass
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        pass
    if isinstance(v, (date, datetime)):
        return str(v)
    return str(v)


@register_tool(
    name="cluster_analysis",
    description="Кластеризация данных: K-Means или DBSCAN с автоматическим выбором количества кластеров (elbow method). Показывает профиль каждого кластера, размеры, ключевые отличия. Автоматически строит scatter-визуализацию.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "columns": {"type": "string", "description": "Числовые колонки для кластеризации через запятую"},
            "method": {"type": "string", "enum": ["kmeans", "dbscan"], "description": "Метод кластеризации (по умолчанию kmeans)"},
            "n_clusters": {"type": "integer", "description": "Количество кластеров для K-Means (auto = elbow method, по умолчанию auto)"},
            "min_cluster_size": {"type": "integer", "description": "Минимальный размер кластера для DBSCAN (по умолчанию 5)"},
            "sample_size": {"type": "integer", "description": "Максимальное количество строк для анализа (по умолчанию 5000)"},
        },
        "required": ["table_name", "columns"],
    },
)
def cluster_analysis(
    session: Session,
    table_name: str,
    columns: str,
    method: str = "kmeans",
    n_clusters: int = 0,
    min_cluster_size: int = 5,
    sample_size: int = 5000,
) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    try:
        import numpy as np
        from sklearn.cluster import KMeans, DBSCAN
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        return "Для кластеризации нужны numpy и scikit-learn."

    conn = session.conn
    cols = [c.strip() for c in columns.split(",")]

    cols_select = ", ".join(f'"{c}"' for c in cols)
    not_null_cond = " AND ".join(f'"{c}" IS NOT NULL' for c in cols)
    try:
        result = conn.execute(
            f'SELECT {cols_select} FROM "{table_name}" '
            f'WHERE {not_null_cond} '
            f'LIMIT {sample_size}'
        )
        rows = result.fetchall()
    except Exception as e:
        return f"Ошибка: {e}"

    if len(rows) < 10:
        return "Недостаточно данных для кластеризации (минимум 10 строк)."

    X = np.array([[float(r[i]) for i in range(len(cols))] for r in rows])
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    if method == "kmeans":
        if n_clusters <= 0:
            inertias = []
            K_range = range(2, min(11, len(rows) // 5 + 1))
            for k in K_range:
                km = KMeans(n_clusters=k, random_state=42, n_init=10)
                km.fit(X_scaled)
                inertias.append(km.inertia_)

            diffs = [inertias[i] - inertias[i + 1] for i in range(len(inertias) - 1)]
            if diffs:
                best_k = list(K_range)[1 + max(range(len(diffs)), key=lambda i: diffs[i])]
            else:
                best_k = 3
            n_clusters = best_k

        model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = model.fit_predict(X_scaled)
    else:
        model = DBSCAN(min_samples=min_cluster_size)
        labels = model.fit_predict(X_scaled)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

    unique_labels = sorted(set(labels))
    out = [f"# Кластеризация: {table_name}", ""]
    out.append(f"Метод: {method.upper()}")
    out.append(f"Найдено кластеров: {n_clusters}")
    out.append(f"Анализируемых строк: {len(rows)}")
    out.append(f"Признаки: {', '.join(cols)}")
    out.append("")

    cluster_profiles = []
    for label in unique_labels:
        if label == -1:
            out.append("## Шум (DBSCAN outliers)")
            mask = labels == label
            out.append(f"Строк: {mask.sum()}")
            continue

        mask = labels == label
        cluster_rows = X[mask]
        profile = {"cluster": int(label), "size": int(mask.sum())}

        out.append(f"## Кластер {label} ({mask.sum()} строк, {round(mask.sum() / len(rows) * 100, 1)}%)")
        for i, col in enumerate(cols):
            values = cluster_rows[:, i]
            profile[col + "_mean"] = round(float(np.mean(values)), 4)
            profile[col + "_std"] = round(float(np.std(values)), 4)
            out.append(f"  {col}: mean={round(float(np.mean(values)), 2)}, std={round(float(np.std(values)), 2)}")

        cluster_profiles.append(profile)
        out.append("")

    if len(cols) >= 2:
        chart_data = []
        x_col, y_col = cols[0], cols[1]
        for i, row in enumerate(rows[:500]):
            chart_data.append({
                x_col: _safe_val(row[0]),
                y_col: _safe_val(row[1]),
                "cluster": f"C{labels[i]}" if labels[i] >= 0 else "noise",
            })

        chart_spec = {
            "type": "scatter",
            "title": f"Кластеры: {x_col} vs {y_col}",
            "data": chart_data,
            "xKey": x_col,
            "yKeys": [y_col],
            "scatterGroup": "cluster",
        }
        out.append(f"__CHART_DATA__\n{json.dumps(chart_spec, ensure_ascii=False, default=str)}\n__END_CHART_DATA__")

    try:
        conn.execute(f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS _cluster INTEGER DEFAULT NULL')
        rowids = conn.execute(f'SELECT rowid FROM "{table_name}" LIMIT {sample_size}').fetchall()
        for i, (rid,) in enumerate(rowids):
            if i < len(labels):
                conn.execute(f'UPDATE "{table_name}" SET _cluster = ? WHERE rowid = ?', [int(labels[i]), rid])
        out.append(f"\nКластеры записаны в колонку _cluster таблицы {table_name}.")
    except Exception as e:
        out.append(f"\nНе удалось записать кластеры: {e}")

    return "\n".join(out)

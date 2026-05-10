from __future__ import annotations

import json
import math
from datetime import date, datetime

from app.session import Session
from .registry import register_tool


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
    name="feature_importance",
    description="Анализ важности признаков: определяет какие колонки сильнее всего влияют на целевую переменную. Random Forest importance + permutation importance. Показывает ранжированный список с bar chart.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "target_column": {"type": "string", "description": "Целевая колонка (зависимая переменная)"},
            "feature_columns": {"type": "string", "description": "Колонки-признаки через запятую (необязательно, по умолчанию все числовые кроме целевой)"},
            "method": {"type": "string", "enum": ["forest", "permutation", "both"], "description": "Метод: forest (Random Forest), permutation, both (по умолчанию both)"},
            "sample_size": {"type": "integer", "description": "Макс. строк для анализа (по умолчанию 5000)"},
        },
        "required": ["table_name", "target_column"],
    },
)
def feature_importance(
    session: Session,
    table_name: str,
    target_column: str,
    feature_columns: str = "",
    method: str = "both",
    sample_size: int = 5000,
) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    try:
        import numpy as np
        from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
        from sklearn.inspection import permutation_importance
        from sklearn.model_selection import train_test_split
    except ImportError:
        return "Нужны numpy и scikit-learn."

    conn = session.conn

    schema = conn.execute(f'DESCRIBE "{table_name}"').fetchall()
    numeric_types = {"integer", "bigint", "smallint", "float", "double", "decimal", "numeric", "real", "hugeint"}
    all_numeric = [s[0] for s in schema if any(t in s[1].lower() for t in numeric_types)]

    if feature_columns.strip():
        features = [c.strip() for c in feature_columns.split(",")]
    else:
        features = [c for c in all_numeric if c != target_column]

    if not features:
        return "Нет числовых колонок-признаков для анализа."

    all_cols = features + [target_column]
    cols_select = ", ".join(f'"{c}"' for c in all_cols)
    not_null_cond = " AND ".join(f'"{c}" IS NOT NULL' for c in all_cols)
    try:
        result = conn.execute(
            f'SELECT {cols_select} FROM "{table_name}" '
            f'WHERE {not_null_cond} '
            f'LIMIT {sample_size}'
        )
        rows = result.fetchall()
    except Exception as e:
        return f"Ошибка: {e}"

    if len(rows) < 30:
        return "Недостаточно данных (минимум 30 строк)."

    X = np.array([[float(r[i]) for i in range(len(features))] for r in rows])
    y = np.array([float(r[len(features)]) for r in rows])

    is_classification = len(set(y)) <= 20 and all(float(v).is_integer() for v in y)
    if is_classification:
        y = y.astype(int)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    out = [f"# Важность признаков для {target_column}", ""]
    out.append(f"Тип задачи: {'Классификация' if is_classification else 'Регрессия'}")
    out.append(f"Строк: {len(rows)}, Признаков: {len(features)}")
    out.append("")

    forest_cls = RandomForestClassifier if is_classification else RandomForestRegressor
    rf = forest_cls(n_estimators=100, random_state=42, max_depth=10)
    rf.fit(X_train, y_train)

    score = rf.score(X_test, y_test)
    out.append(f"Качество модели (R²/Accuracy): {round(float(score), 4)}")
    out.append("")

    if method in ("forest", "both"):
        out.append("## Random Forest Importance")
        importances = rf.feature_importances_
        indices = np.argsort(importances)[::-1]
        for idx in indices:
            out.append(f"  **{features[idx]}**: {round(float(importances[idx]), 4)}")
        out.append("")

    if method in ("permutation", "both"):
        out.append("## Permutation Importance")
        try:
            perm = permutation_importance(rf, X_test, y_test, n_repeats=10, random_state=42)
            perm_indices = np.argsort(perm.importances_mean)[::-1]
            for idx in perm_indices:
                mean_val = round(float(perm.importances_mean[idx]), 4)
                std_val = round(float(perm.importances_std[idx]), 4)
                out.append(f"  **{features[idx]}**: {mean_val} ± {std_val}")
        except Exception as e:
            out.append(f"  Ошибка: {e}")
        out.append("")

    chart_data = []
    indices = np.argsort(importances)[::-1]
    for idx in indices:
        chart_data.append({
            "feature": features[idx],
            "importance": _safe_val(importances[idx]),
        })

    chart_spec = {
        "type": "bar",
        "title": f"Важность признаков → {target_column}",
        "data": chart_data,
        "xKey": "feature",
        "yKeys": ["importance"],
        "horizontal": True,
    }

    out.append(f"__CHART_DATA__\n{json.dumps(chart_spec, ensure_ascii=False, default=str)}\n__END_CHART_DATA__")

    return "\n".join(out)

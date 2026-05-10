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
    name="predict_trend",
    description="Прогнозирование: строит модель (линейная или полиномиальная регрессия) на основе временного ряда и прогнозирует значения на N периодов вперёд. Показывает доверительные интервалы. Автоматически строит график с прогнозом.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "date_column": {"type": "string", "description": "Колонка с датой"},
            "value_column": {"type": "string", "description": "Числовая колонка для прогноза"},
            "period": {"type": "string", "enum": ["day", "week", "month", "year"], "description": "Период агрегации (по умолчанию month)"},
            "forecast_periods": {"type": "integer", "description": "Количество периодов для прогноза (по умолчанию 6)"},
            "model_type": {"type": "string", "enum": ["linear", "polynomial"], "description": "Тип модели (по умолчанию linear)"},
            "polynomial_degree": {"type": "integer", "description": "Степень полинома для polynomial модели (по умолчанию 2)"},
        },
        "required": ["table_name", "date_column", "value_column"],
    },
)
def predict_trend(
    session: Session,
    table_name: str,
    date_column: str,
    value_column: str,
    period: str = "month",
    forecast_periods: int = 6,
    model_type: str = "linear",
    polynomial_degree: int = 2,
) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    try:
        import numpy as np
        from sklearn.linear_model import LinearRegression
        from sklearn.preprocessing import PolynomialFeatures
    except ImportError:
        return "Для прогнозирования нужны numpy и scikit-learn. Установите: pip install numpy scikit-learn"

    conn = session.conn

    try:
        ts_sql = (
            f"SELECT DATE_TRUNC('{period}', \"{date_column}\") as period_start, "
            f'AVG("{value_column}") as avg_val '
            f'FROM "{table_name}" '
            f'WHERE "{date_column}" IS NOT NULL AND "{value_column}" IS NOT NULL '
            f'GROUP BY period_start ORDER BY period_start'
        )
        result = conn.execute(ts_sql)
        rows = result.fetchall()
    except Exception as e:
        return f"Ошибка запроса: {e}"

    if len(rows) < 3:
        return "Недостаточно данных для прогноза (нужно минимум 3 периода)."

    periods = [str(r[0]) for r in rows]
    values = [float(r[1]) for r in rows]
    X = np.array(range(len(values))).reshape(-1, 1)
    y = np.array(values)

    if model_type == "polynomial" and polynomial_degree > 1:
        poly = PolynomialFeatures(degree=polynomial_degree, include_bias=False)
        X_transformed = poly.fit_transform(X)
        model = LinearRegression()
        model.fit(X_transformed, y)

        X_future = np.array(range(len(values), len(values) + forecast_periods)).reshape(-1, 1)
        X_future_transformed = poly.transform(X_future)
        predictions = model.predict(X_future_transformed)
        y_pred = model.predict(X_transformed)
    else:
        model = LinearRegression()
        model.fit(X, y)
        X_future = np.array(range(len(values), len(values) + forecast_periods)).reshape(-1, 1)
        predictions = model.predict(X_future)
        y_pred = model.predict(X)

    residuals = y - y_pred
    std_err = np.std(residuals) if len(residuals) > 2 else 0
    z = 1.96

    out = [f"# Прогноз: {value_column} по {date_column}", ""]
    out.append(f"Модель: {'Полиномиальная (степень ' + str(polynomial_degree) + ')' if model_type == 'polynomial' else 'Линейная'}")
    out.append(f"Обучающая выборка: {len(values)} периодов")
    out.append(f"Прогноз на: {forecast_periods} периодов")
    out.append(f"Стандартная ошибка: {round(std_err, 4)}")

    slope = model.coef_[0] if model_type == "linear" else model.coef_[-1]
    out.append(f"Наклон тренда: {round(float(slope), 4)} ({'рост' if slope > 0 else 'падение' if slope < 0 else 'стабильно'})")

    r_squared = 1 - np.sum(residuals ** 2) / np.sum((y - np.mean(y)) ** 2)
    out.append(f"R² (качество модели): {round(float(r_squared), 4)}")

    if r_squared < 0.3:
        out.append("⚠️ Низкое качество модели — прогноз ненадёжен. Попробуйте polynomial или другой период.")
    elif r_squared < 0.6:
        out.append("⚠️ Умеренное качество модели — прогноз примерный.")
    else:
        out.append("✅ Хорошее качество модели — прогноз достоверен.")

    out.append("")
    out.append("## Прогнозные значения")
    out.append("")
    out.append("Период | Прогноз | 95% ДИ нижн | 95% ДИ верхн")
    out.append("---|---|---|---")

    forecast_data = []
    for i, pred in enumerate(predictions):
        lower = pred - z * std_err
        upper = pred + z * std_err
        pred_val = round(float(pred), 2)
        lower_val = round(float(lower), 2)
        upper_val = round(float(upper), 2)
        period_label = f"Период +{i + 1}"
        out.append(f"{period_label} | {pred_val} | {lower_val} | {upper_val}")
        forecast_data.append({
            "period": period_label,
            "value": _safe_val(pred),
            "lower": _safe_val(lower),
            "upper": _safe_val(upper),
            "type": "forecast",
        })

    chart_data = []
    for i, (p, v) in enumerate(zip(periods, values)):
        chart_data.append({
            "period": p[:10] if len(p) > 10 else p,
            "value": _safe_val(v),
            "lower": _safe_val(v),
            "upper": _safe_val(v),
            "type": "actual",
        })
    for fd in forecast_data:
        chart_data.append(fd)

    chart_spec = {
        "type": "area",
        "title": f"Прогноз: {value_column}",
        "data": chart_data,
        "xKey": "period",
        "yKeys": ["value", "lower", "upper"],
        "isForecast": True,
    }

    out.append("")
    out.append(f"__CHART_DATA__\n{json.dumps(chart_spec, ensure_ascii=False, default=str)}\n__END_CHART_DATA__")

    return "\n".join(out)

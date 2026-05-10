from __future__ import annotations

from app.session import Session
from .registry import register_tool


@register_tool(
    name="distribution_analysis",
    description="Детальный анализ распределения числовых колонок: гистограмма (бакеты + частоты), асимметрия (skewness), эксцесс (kurtosis), проверка на нормальность, тип распределения. Помогает понять форму данных.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "columns": {"type": "string", "description": "Числовые колонки через запятую (необязательно, по умолчанию все числовые)"},
            "bins": {"type": "integer", "description": "Количество бакетов для гистограммы (по умолчанию 10)"},
        },
        "required": ["table_name"],
    },
)
def distribution_analysis(session: Session, table_name: str, columns: str = "", bins: int = 10) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn
    schema = conn.execute(f'DESCRIBE "{table_name}"').fetchall()
    numeric_types = {"integer", "bigint", "smallint", "float", "double", "decimal", "numeric", "real", "hugeint"}
    numeric_cols = [s[0] for s in schema if any(t in s[1].lower() for t in numeric_types)]

    if columns.strip():
        requested = [c.strip() for c in columns.split(",")]
        numeric_cols = [c for c in requested if c in numeric_cols]

    if not numeric_cols:
        return "Числовые колонки не найдены."

    bins = min(max(bins, 3), 30)
    results = []

    for col in numeric_cols:
        lines = [f"### {col}", ""]

        count = conn.execute(f'SELECT COUNT(*), COUNT("{col}") FROM "{table_name}"').fetchone()
        total, non_null = count[0], count[1]
        null_pct = round((total - non_null) / total * 100, 1) if total else 0
        lines.append(f"Заполненность: {non_null}/{total} ({100 - null_pct}%)")

        if non_null == 0:
            lines.append("Нет данных для анализа.")
            results.append("\n".join(lines))
            continue

        try:
            stats = conn.execute(
                f'SELECT MIN("{col}"), MAX("{col}"), AVG("{col}"), STDDEV("{col}"), '
                f'MEDIAN("{col}"), SKEWNESS("{col}"), KURTOSIS("{col}") '
                f'FROM "{table_name}" WHERE "{col}" IS NOT NULL'
            ).fetchone()
        except Exception as e:
            lines.append(f"Ошибка: {e}")
            results.append("\n".join(lines))
            continue

        mn, mx, avg, stddev, median, skew, kurt = stats

        lines.append(f"Min: {mn}, Max: {mx}, Range: {mx - mn if mn is not None and mx is not None else 'N/A'}")
        lines.append(f"Mean: {round(avg, 4)}, Median: {median}, StdDev: {round(stddev, 4) if stddev else 0}")

        if skew is not None:
            skew_abs = abs(skew)
            if skew_abs < 0.5:
                skew_desc = "симметричное (≈ нормальное)"
            elif skew < 0:
                skew_desc = "скошено влево (длинный хвост слева)"
            else:
                skew_desc = "скошено вправо (длинный хвост справа)"
            lines.append(f"Асимметрия (skewness): {round(skew, 4)} — {skew_desc}")

        if kurt is not None:
            excess_kurt = kurt - 3 if kurt else 0
            if abs(excess_kurt) < 1:
                kurt_desc = "близко к нормальному (mesokurtic)"
            elif excess_kurt > 0:
                kurt_desc = "тяжёлые хвосты, острый пик (leptokurtic)"
            else:
                kurt_desc = "лёгкие хвосты, плоская вершина (platykurtic)"
            lines.append(f"Эксцесс (kurtosis): {round(kurt, 4)} (excess: {round(excess_kurt, 4)}) — {kurt_desc}")

        dist_type = "Возможно нормальное"
        if skew is not None and kurt is not None:
            if abs(skew) > 1 or abs((kurt or 0) - 3) > 3:
                dist_type = "Ненормальное"
            elif abs(skew) > 0.5:
                dist_type = "Умеренно скошенное"
        lines.append(f"Тип распределения: {dist_type}")

        try:
            width = (mx - mn) / bins if mx != mn else 1
            hist = conn.execute(
                f'SELECT FLOOR(("{col}" - {mn}) / {width}) as bucket, '
                f'COUNT(*) as freq, '
                f'MIN("{col}") as bucket_min, '
                f'MAX("{col}") as bucket_max '
                f'FROM "{table_name}" WHERE "{col}" IS NOT NULL '
                f'GROUP BY bucket ORDER BY bucket'
            ).fetchall()

            if hist:
                lines.append("")
                lines.append("Гистограмма:")
                max_freq = max(h[1] for h in hist)
                bar_width = 30
                for bucket, freq, bmin, bmax in hist:
                    bar_len = int(freq / max_freq * bar_width) if max_freq else 0
                    bar = "█" * bar_len
                    label = f"[{round(bmin, 2)} - {round(bmax, 2)}]"
                    lines.append(f"  {label:>25} {freq:>6} {bar}")
        except Exception:
            pass

        results.append("\n".join(lines))

    header = f"Анализ распределения: {table_name}\n\n"
    return header + "\n\n".join(results)

from __future__ import annotations

from app.session import Session
from .registry import register_tool


@register_tool(
    name="statistical_test",
    description="Статистические тесты: t-test, Mann-Whitney U, Kolmogorov-Smirnov, chi-square между группами. Интерпретация p-value и статистической значимости. Для сравнения двух выборок или проверки распределений.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "test": {"type": "string", "enum": ["ttest", "mannwhitney", "ks", "chi2"], "description": "Тип теста: ttest (t-тест для средних), mannwhitney (непараметрический), ks (сравнение распределений), chi2 (хи-квадрат для категорий)"},
            "column": {"type": "string", "description": "Числовая колонка для теста (для ttest/mannwhitney/ks)"},
            "group_column": {"type": "string", "description": "Колонка для группировки (категориальная, для сравнения групп)"},
            "group_a": {"type": "string", "description": "Значение группы A (необязательно, по умолчанию первая)"},
            "group_b": {"type": "string", "description": "Значение группы B (необязательно, по умолчанию вторая)"},
        },
        "required": ["table_name", "test"],
    },
)
def statistical_test(
    session: Session,
    table_name: str,
    test: str,
    column: str = "",
    group_column: str = "",
    group_a: str = "",
    group_b: str = "",
) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    try:
        import numpy as np
        from scipy import stats
    except ImportError:
        return "Нужны numpy и scipy."

    conn = session.conn

    test_names = {"ttest": "t-тест (Стьюдента)", "mannwhitney": "Mann-Whitney U", "ks": "Kolmogorov-Smirnov", "chi2": "Хи-квадрат"}
    out = [f"# Статистический тест: {test_names.get(test, test)}", ""]

    if test == "chi2":
        if not column or not group_column:
            return "Для chi2 нужны column и group_column."
        try:
            contingency = conn.execute(
                f'SELECT "{group_column}", "{column}", COUNT(*) as cnt '
                f'FROM "{table_name}" WHERE "{group_column}" IS NOT NULL AND "{column}" IS NOT NULL '
                f'GROUP BY "{group_column}", "{column}" ORDER BY "{group_column}", "{column}"'
            ).fetchall()

            groups = sorted(set(r[0] for r in contingency))
            categories = sorted(set(r[1] for r in contingency))

            if len(groups) < 2:
                return "Нужно минимум 2 группы для chi2."

            matrix = np.zeros((len(groups), len(categories)))
            for r in contingency:
                gi = groups.index(r[0])
                ci = categories.index(r[1])
                matrix[gi, ci] = r[2]

            chi2, p, dof, expected = stats.chi2_contingency(matrix)

            out.append(f"Группы ({group_column}): {', '.join(str(g) for g in groups)}")
            out.append(f"Категории ({column}): {', '.join(str(c) for c in categories)}")
            out.append("")
            out.append(f"Хи-квадрат: {round(chi2, 4)}")
            out.append(f"Степени свободы: {dof}")
            out.append(f"p-value: {p:.6f}" if p >= 0.000001 else f"p-value: {p:.2e}")

            if p < 0.001:
                out.append("**Результат**: Статистически значимая связь (p < 0.001) ★★★")
            elif p < 0.01:
                out.append("**Результат**: Статистически значимая связь (p < 0.01) ★★")
            elif p < 0.05:
                out.append("**Результат**: Статистически значимая связь (p < 0.05) ★")
            else:
                out.append("**Результат**: Связь не значима (p >= 0.05)")

            cramers_v = (chi2 / (matrix.sum() * (min(len(groups), len(categories)) - 1))) ** 0.5 if matrix.sum() else 0
            strength = "слабая" if cramers_v < 0.3 else "умеренная" if cramers_v < 0.5 else "сильная"
            out.append(f"Cramer's V: {round(cramers_v, 4)} — {strength} связь")
        except Exception as e:
            return f"Ошибка: {e}"
    else:
        if not column or not group_column:
            return f"Для {test} нужны column и group_column."

        if not group_a or not group_b:
            groups = conn.execute(
                f'SELECT DISTINCT "{group_column}" FROM "{table_name}" '
                f'WHERE "{group_column}" IS NOT NULL ORDER BY "{group_column}" LIMIT 2'
            ).fetchall()
            if len(groups) < 2:
                return f"Нужно минимум 2 группы в {group_column}."
            group_a = str(groups[0][0])
            group_b = str(groups[1][0])

        ga_escaped = group_a.replace("'", "''")
        gb_escaped = group_b.replace("'", "''")

        try:
            vals_a = [r[0] for r in conn.execute(
                f'SELECT "{column}" FROM "{table_name}" '
                f'WHERE "{group_column}" = \'{ga_escaped}\' AND "{column}" IS NOT NULL'
            ).fetchall()]
            vals_b = [r[0] for r in conn.execute(
                f'SELECT "{column}" FROM "{table_name}" '
                f'WHERE "{group_column}" = \'{gb_escaped}\' AND "{column}" IS NOT NULL'
            ).fetchall()]
        except Exception as e:
            return f"Ошибка: {e}"

        if len(vals_a) < 2 or len(vals_b) < 2:
            return "Недостаточно данных в одной из групп."

        arr_a = np.array(vals_a, dtype=float)
        arr_b = np.array(vals_b, dtype=float)

        out.append(f"Переменная: {column}")
        out.append(f"Группы: {group_a} (n={len(vals_a)}) vs {group_b} (n={len(vals_b)})")
        out.append("")
        out.append(f"Группа {group_a}: mean={round(float(np.mean(arr_a)), 4)}, median={round(float(np.median(arr_a)), 4)}, std={round(float(np.std(arr_a)), 4)}")
        out.append(f"Группа {group_b}: mean={round(float(np.mean(arr_b)), 4)}, median={round(float(np.median(arr_b)), 4)}, std={round(float(np.std(arr_b)), 4)}")
        out.append("")

        if test == "ttest":
            stat, p = stats.ttest_ind(arr_a, arr_b)
            out.append(f"t-статистика: {round(float(stat), 4)}")
            out.append(f"p-value: {p:.6f}" if p >= 0.000001 else f"p-value: {p:.2e}")
            diff = round(float(np.mean(arr_a) - np.mean(arr_b)), 4)
            out.append(f"Разница средних: {diff}")

        elif test == "mannwhitney":
            stat, p = stats.mannwhitneyu(arr_a, arr_b, alternative='two-sided')
            out.append(f"U-статистика: {round(float(stat), 4)}")
            out.append(f"p-value: {p:.6f}" if p >= 0.000001 else f"p-value: {p:.2e}")

        elif test == "ks":
            stat, p = stats.ks_2samp(arr_a, arr_b)
            out.append(f"KS-статистика: {round(float(stat), 4)}")
            out.append(f"p-value: {p:.6f}" if p >= 0.000001 else f"p-value: {p:.2e}")
            out.append("Интерпретация: максимальная разница между кумулятивными распределениями групп")

        out.append("")
        if p < 0.001:
            out.append("**Результат**: Различия статистически значимы (p < 0.001) ★★★")
        elif p < 0.01:
            out.append("**Результат**: Различия статистически значимы (p < 0.01) ★★")
        elif p < 0.05:
            out.append("**Результат**: Различия статистически значимы (p < 0.05) ★")
        else:
            out.append("**Результат**: Различия не значимы (p >= 0.05) — нельзя отвергнуть нулевую гипотезу")

        effect_size = abs(float(np.mean(arr_a) - np.mean(arr_b))) / max(float(np.std(np.concatenate([arr_a, arr_b]))), 0.001)
        out.append(f"Cohen's d: {round(effect_size, 4)} ({'большой' if effect_size >= 0.8 else 'средний' if effect_size >= 0.5 else 'малый'} эффект)")

    return "\n".join(out)

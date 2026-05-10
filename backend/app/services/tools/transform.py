from __future__ import annotations

from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="transform_data",
    description="Трансформация данных: нормализация (min-max, z-score), one-hot encoding, заполнение пропусков, создание производных колонок (извлечь год/месяц/день из дат, binning). Создаёт новую таблицу с результатами.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Исходная таблица"},
            "operations": {"type": "string", "description": "Операции через точку с запятой. Формат: normalize:col:minmax|zscore; fillna:col:mean|median|mode|0; extract:date_col:year|month|day|weekday; onehot:col; bin:col:5; derive:new_col=expression"},
            "output_table": {"type": "string", "description": "Имя новой таблицы (по умолчанию исходная_transformed)"},
        },
        "required": ["table_name", "operations"],
    },
)
def transform_data(session: Session, table_name: str, operations: str, output_table: str = "") -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn
    if not output_table:
        output_table = f"{table_name}_transformed"

    output_table = output_table.replace(" ", "_").replace("-", "_")

    ops = [op.strip() for op in operations.split(";") if op.strip()]
    results = []

    try:
        conn.execute(f'CREATE TABLE "{output_table}" AS SELECT * FROM "{table_name}"')
    except Exception as e:
        return f"Ошибка создания таблицы: {e}"

    for op in ops:
        parts = op.split(":")
        if len(parts) < 2:
            results.append(f"Пропущена некорректная операция: {op}")
            continue

        action = parts[0].lower()

        if action == "normalize" and len(parts) >= 3:
            col = parts[1]
            method = parts[2].lower()
            try:
                if method == "minmax":
                    mn_mx = conn.execute(f'SELECT MIN("{col}"), MAX("{col}") FROM "{output_table}" WHERE "{col}" IS NOT NULL').fetchone()
                    if mn_mx and mn_mx[1] != mn_mx[0]:
                        col_min, col_max = mn_mx[0], mn_mx[1]
                        range_val = col_max - col_min
                        conn.execute(
                            f'UPDATE "{output_table}" SET "{col}" = ("{col}" - {col_min}) / {range_val} WHERE "{col}" IS NOT NULL'
                        )
                        results.append(f"normalize:{col}:minmax ✓ (0-1)")
                    else:
                        results.append(f"normalize:{col}: все значения одинаковые")
                elif method == "zscore":
                    stats = conn.execute(f'SELECT AVG("{col}"), STDDEV("{col}") FROM "{output_table}" WHERE "{col}" IS NOT NULL').fetchone()
                    if stats and stats[1] and stats[1] != 0:
                        conn.execute(
                            f'UPDATE "{output_table}" SET "{col}" = ("{col}" - {stats[0]}) / {stats[1]} WHERE "{col}" IS NOT NULL'
                        )
                        results.append(f"normalize:{col}:zscore ✓ (mean=0, std=1)")
                    else:
                        results.append(f"normalize:{col}: stddev=0, невозможно")
            except Exception as e:
                results.append(f"normalize:{col}: ошибка {e}")

        elif action == "fillna" and len(parts) >= 3:
            col = parts[1]
            fill_method = parts[2].lower()
            try:
                if fill_method == "mean":
                    val = conn.execute(f'SELECT AVG("{col}") FROM "{output_table}" WHERE "{col}" IS NOT NULL').fetchone()[0]
                    if val is not None:
                        conn.execute(f'UPDATE "{output_table}" SET "{col}" = {val} WHERE "{col}" IS NULL')
                        results.append(f"fillna:{col}:mean ({round(val, 4)}) ✓")
                elif fill_method == "median":
                    val = conn.execute(f'SELECT MEDIAN("{col}") FROM "{output_table}" WHERE "{col}" IS NOT NULL').fetchone()[0]
                    if val is not None:
                        conn.execute(f'UPDATE "{output_table}" SET "{col}" = {val} WHERE "{col}" IS NULL')
                        results.append(f"fillna:{col}:median ({round(val, 4)}) ✓")
                elif fill_method == "mode":
                    val = conn.execute(
                        f'SELECT "{col}" FROM "{output_table}" WHERE "{col}" IS NOT NULL '
                        f'GROUP BY "{col}" ORDER BY COUNT(*) DESC LIMIT 1'
                    ).fetchone()
                    if val:
                        val_escaped = str(val[0]).replace("'", "''")
                        conn.execute(f'UPDATE "{output_table}" SET "{col}" = \'{val_escaped}\' WHERE "{col}" IS NULL')
                        results.append(f"fillna:{col}:mode ({val[0]}) ✓")
                else:
                    default_val = fill_method
                    try:
                        default_float = float(default_val)
                        conn.execute(f'UPDATE "{output_table}" SET "{col}" = {default_float} WHERE "{col}" IS NULL')
                    except ValueError:
                        conn.execute(f"UPDATE \"{output_table}\" SET \"{col}\" = '{default_val}' WHERE \"{col}\" IS NULL")
                    results.append(f"fillna:{col}:{default_val} ✓")
            except Exception as e:
                results.append(f"fillna:{col}: ошибка {e}")

        elif action == "extract" and len(parts) >= 3:
            col = parts[1]
            part = parts[2].lower()
            try:
                new_col = f"{col}_{part}"
                extract_map = {
                    "year": f'YEAR("{col}")',
                    "month": f'MONTH("{col}")',
                    "day": f'DAY("{col}")',
                    "weekday": f'DAYOFWEEK("{col}")',
                    "hour": f'HOUR("{col}")',
                    "quarter": f'QUARTER("{col}")',
                }
                if part in extract_map:
                    conn.execute(f'ALTER TABLE "{output_table}" ADD COLUMN IF NOT EXISTS "{new_col}" INTEGER')
                    conn.execute(f'UPDATE "{output_table}" SET "{new_col}" = {extract_map[part]} WHERE "{col}" IS NOT NULL')
                    results.append(f"extract:{col}:{part} → {new_col} ✓")
                else:
                    results.append(f"extract:{col}: неизвестная часть '{part}' (год/месяц/день/день_недели/час/квартал)")
            except Exception as e:
                results.append(f"extract:{col}:{part}: ошибка {e}")

        elif action == "onehot" and len(parts) >= 2:
            col = parts[1]
            try:
                values = conn.execute(
                    f'SELECT DISTINCT "{col}" FROM "{output_table}" WHERE "{col}" IS NOT NULL ORDER BY "{col}" LIMIT 20'
                ).fetchall()
                for (val,) in values:
                    safe_name = f"{col}_{str(val).replace(' ', '_').replace('-', '_')}"
                    val_escaped = str(val).replace("'", "''")
                    conn.execute(f'ALTER TABLE "{output_table}" ADD COLUMN IF NOT EXISTS "{safe_name}" INTEGER DEFAULT 0')
                    conn.execute(f'UPDATE "{output_table}" SET "{safe_name}" = 1 WHERE "{col}" = \'{val_escaped}\'')
                results.append(f"onehot:{col} → {len(values)} колонок ✓")
            except Exception as e:
                results.append(f"onehot:{col}: ошибка {e}")

        elif action == "bin" and len(parts) >= 2:
            col = parts[1]
            n_bins = int(parts[2]) if len(parts) >= 3 else 5
            try:
                new_col = f"{col}_bin"
                conn.execute(f'ALTER TABLE "{output_table}" ADD COLUMN IF NOT EXISTS "{new_col}" VARCHAR')
                conn.execute(
                    f'UPDATE "{output_table}" SET "{new_col}" = CAST(NTILE({n_bins}) OVER (ORDER BY "{col}") AS VARCHAR) '
                    f'WHERE "{col}" IS NOT NULL'
                )
                results.append(f"bin:{col} → {new_col} ({n_bins} групп) ✓")
            except Exception as e:
                results.append(f"bin:{col}: ошибка {e}")

        elif action == "derive" and len(parts) >= 2:
            expr = ":".join(parts[1:])
            try:
                if "=" in expr:
                    new_col, formula = expr.split("=", 1)
                    new_col = new_col.strip()
                    conn.execute(f'ALTER TABLE "{output_table}" ADD COLUMN IF NOT EXISTS "{new_col}" DOUBLE')
                    conn.execute(f'UPDATE "{output_table}" SET "{new_col}" = {formula}')
                    results.append(f"derive:{new_col} = {formula} ✓")
                else:
                    results.append(f"derive: нужен формат new_col=expression")
            except Exception as e:
                results.append(f"derive: ошибка {e}")

        else:
            results.append(f"Неизвестная операция: {op}")

    out = [
        f"# Трансформация: {table_name} → {output_table}",
        "",
        "Выполненные операции:",
    ]
    for r in results:
        out.append(f"  {r}")

    new_count = conn.execute(f'SELECT COUNT(*) FROM "{output_table}"').fetchone()[0]
    new_schema = conn.execute(f'DESCRIBE "{output_table}"').fetchall()
    out.append(f"\nРезультат: {new_count:,} строк, {len(new_schema)} колонок")
    out.append("")
    out.append("Новые колонки:")
    orig_cols = {s[0] for s in conn.execute(f'DESCRIBE "{table_name}"').fetchall()}
    for s in new_schema:
        if s[0] not in orig_cols:
            out.append(f"  + {s[0]}: {s[1]}")

    out.append(f"\nТеперь можно анализировать таблицу `{output_table}`.")

    return "\n".join(out)

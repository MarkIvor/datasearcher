from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx

from .config import settings
from .prompts.system import build_classify_prompt, build_generate_sql_prompt

if TYPE_CHECKING:
    from .session import Session


class LLMClient:
    """OpenAI-compatible LLM-клиент для classify_rows / generate_sql.

    В DataSearcher эти задачи резолвятся LLM-сервисом в цикле инструментов.
    В MCP хост-модель не вызывает их сама, поэтому используется отдельный
    LLM-клиент (настраивается через LLM_BASE_URL/LLM_API_KEY/LLM_MODEL).
    """

    def __init__(self):
        self.base_url = (settings.llm_base_url or "").rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.enabled = bool(self.base_url and self.model)

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def _single_completion(self, messages: list[dict]) -> str:
        if not self.enabled:
            raise RuntimeError(
                "LLM не настроен. Задайте LLM_BASE_URL и LLM_MODEL "
                "(OpenAI-compatible API)."
            )
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": settings.llm_max_tokens,
            "temperature": 0.1,
            "stream": False,
        }
        url = f"{self.base_url}/chat/completions"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def handle_classify(self, session: "Session", task_data: str) -> str:
        lines = task_data.split("\n")
        params: dict[str, str] = {}
        data_json = ""
        for line in lines:
            if line in ("__CLASSIFY_TASK__", "__END_CLASSIFY_TASK__"):
                continue
            if line.startswith("data="):
                data_json = line[5:]
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                params[key] = val

        columns = json.loads(params.get("columns", "[]"))
        categories = json.loads(params.get("categories", "[]"))
        instruction = params.get("instruction", "")
        table_name = params.get("table_name", "")
        row_ids = json.loads(params.get("row_ids", "[]"))
        data_rows = json.loads(data_json) if data_json else []

        if not data_rows:
            return "Нет данных для классификации."

        batch_size = settings.classify_batch_size
        all_results: list[dict] = []

        for i in range(0, len(data_rows), batch_size):
            batch = data_rows[i:i + batch_size]
            prompt = build_classify_prompt(categories, instruction, columns)
            batch_with_index = []
            for j, row in enumerate(batch):
                row_dict = {columns[k]: v for k, v in enumerate(row) if k < len(columns)}
                row_dict["_row_index"] = i + j
                batch_with_index.append(row_dict)

            try:
                result = await self._single_completion(
                    [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": json.dumps(batch_with_index, ensure_ascii=False, default=str)},
                    ]
                )
                try:
                    parsed = json.loads(result)
                    if isinstance(parsed, list):
                        all_results.extend(parsed)
                except json.JSONDecodeError:
                    all_results.append({"raw_response": result, "batch": i})
            except Exception as e:
                all_results.append({"error": str(e), "batch": i})

        if not all_results:
            return "Классификация не удалась."

        summary: dict[str, int] = {}
        for r in all_results:
            cat = r.get("category", "unknown")
            summary[cat] = summary.get(cat, 0) + 1

        out_lines = [
            f"Классификация завершена ({len(all_results)} строк):",
            "",
            "Распределение по категориям:",
        ]
        for cat, cnt in sorted(summary.items(), key=lambda x: -x[1]):
            pct = round(cnt / len(all_results) * 100, 1)
            out_lines.append(f"  {cat}: {cnt} ({pct}%)")

        out_lines.append("")
        out_lines.append("Примеры классификации:")
        for r in all_results[:10]:
            idx = r.get("row_index", r.get("_row_index", "?"))
            cat = r.get("category", "?")
            reason = r.get("reason", "")
            out_lines.append(f"  Строка {idx}: {cat} — {reason}")

        if table_name and row_ids and all_results:
            try:
                conn = session.conn
                conn.execute(
                    f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS _classification VARCHAR DEFAULT NULL'
                )
                for r in all_results:
                    idx = r.get("row_index")
                    cat = r.get("category")
                    if idx is not None and cat and idx < len(row_ids):
                        rid = row_ids[idx]
                        conn.execute(
                            f'UPDATE "{table_name}" SET _classification = ? WHERE rowid = ?',
                            [cat, rid],
                        )
                out_lines.append("")
                out_lines.append(f"Результаты записаны в колонку _classification таблицы {table_name}.")
            except Exception as e:
                out_lines.append(f"\nНе удалось записать классификацию в таблицу: {e}")

        return "\n".join(out_lines)

    async def handle_generate_sql(self, session: "Session", task_data: str) -> str:
        params: dict[str, str] = {}
        for line in task_data.split("\n"):
            if line.startswith("__GENERATE_SQL_TASK__") or line.startswith("__END_GENERATE_SQL_TASK__"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                params[key] = val

        schema_desc = params.get("schema", "")
        sample = params.get("sample", "")
        description = params.get("description", "")
        table_name = params.get("table_name", "")
        execute = params.get("execute", "true") == "true"

        if not description:
            return "Не указано описание для генерации SQL."

        prompt = build_generate_sql_prompt(schema_desc, sample, description)

        try:
            result = await self._single_completion(
                [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Сгенерируй SQL для: {description}"},
                ]
            )
        except Exception as e:
            return f"Ошибка генерации SQL: {e}"

        try:
            parsed = json.loads(result)
            sql = parsed.get("sql", "")
            explanation = parsed.get("explanation", "")
        except json.JSONDecodeError:
            sql = result.strip()
            explanation = ""

        if not sql:
            return "Не удалось сгенерировать SQL."

        out_lines = [
            f"Сгенерированный SQL для таблицы {table_name}:",
            "",
            f"**Объяснение:** {explanation}" if explanation else "",
            f"```sql\n{sql}\n```",
        ]

        if execute and sql and table_name:
            try:
                conn = session.conn
                query_result = conn.execute(sql)
                if query_result.description:
                    cols = [d[0] for d in query_result.description]
                    rows = query_result.fetchmany(200)
                    from .tools.registry import format_table
                    out_lines.append("")
                    out_lines.append(f"Результат ({len(rows)} строк):")
                    out_lines.append(format_table(cols, rows))
                else:
                    out_lines.append("")
                    out_lines.append("Запрос выполнен успешно (нет возвращаемых данных).")
            except Exception as e:
                out_lines.append(f"\nОшибка выполнения SQL: {e}")
                out_lines.append("Вы можете выполнить запрос вручную через sql_query.")

        return "\n".join(out_lines)


_llm: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm
    if _llm is None:
        _llm = LLMClient()
    return _llm

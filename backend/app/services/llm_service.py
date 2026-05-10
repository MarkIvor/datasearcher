from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx

from ..config import settings
from ..prompts.system import build_classify_prompt, build_generate_sql_prompt, build_system_prompt
from ..session import Session
from .tools.registry import get_tool_definitions, get_tool_handler


class LLMService:
    def __init__(self, base_url: str = "", api_key: str = "", model: str = ""):
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model

    @classmethod
    def from_user_settings(cls, db, user_id: int) -> "LLMService":
        from ..services.auth_service import get_user_llm_settings
        s = get_user_llm_settings(db, user_id)
        return cls(base_url=s["llm_url"], api_key=s["llm_api_key"], model=s["llm_model"])

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _build_messages(self, session: Session, user_message: str) -> list[dict]:
        table_info = [
            {
                "table_name": fi.table_name,
                "file_type": fi.file_type,
                "row_count": fi.row_count,
                "columns": fi.columns,
            }
            for fi in session.files.values()
        ]

        system_prompt = build_system_prompt(table_info)

        messages = [{"role": "system", "content": system_prompt}]

        for msg in getattr(session, "_chat_history", []):
            messages.append(msg)

        messages.append({"role": "user", "content": user_message})
        return messages

    def _compact_history(self, history: list[dict]) -> list[dict]:
        if len(history) <= 60:
            return history

        recent = history[-40:]
        older = history[:-40]

        summary_parts = []
        for msg in older:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if content:
                    summary_parts.append(f"Пользователь: {content[:100]}")
            elif msg.get("role") == "assistant" and msg.get("content"):
                content = msg.get("content", "")
                if content:
                    summary_parts.append(f"Ассистент: {content[:150]}")

        if summary_parts:
            summary = "Сводка предыдущего диалога:\n" + "\n".join(summary_parts[-8:])
            recent.insert(0, {"role": "system", "content": summary})

        return recent

    async def chat(
        self, session: Session, user_message: str
    ) -> AsyncGenerator[tuple, None]:
        messages = self._build_messages(session, user_message)
        tools = get_tool_definitions()
        tool_iterations = 0

        while tool_iterations < settings.max_tool_iterations:
            tool_iterations += 1

            response_content = ""
            tool_calls_data = []

            try:
                async for chunk in self._stream_chat(messages, tools):
                    if chunk[0] == "content":
                        response_content += chunk[1]
                        yield ("token", chunk[1])
                    elif chunk[0] == "tool_calls":
                        tool_calls_data = chunk[1]
            except Exception as e:
                yield ("error", f"LLM ошибка: {e}")
                return

            if not tool_calls_data:
                break

            messages.append({"role": "assistant", "content": response_content or None, "tool_calls": tool_calls_data})

            for tc in tool_calls_data:
                func_name = tc["function"]["name"]
                try:
                    func_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    func_args = {}

                tc_id = tc.get("id", "")
                yield ("tool_call", func_name, func_args, tc_id)
                yield ("step", f"Выполняю {func_name}...")

                handler = get_tool_handler(func_name)
                if handler:
                    try:
                        result = handler(session, **func_args)

                        if result.startswith("__CLASSIFY_TASK__"):
                            yield ("step", "Классификация данных...")
                            result = await self._handle_classify(session, result)
                        elif result.startswith("__GENERATE_SQL_TASK__"):
                            yield ("step", "Генерация SQL...")
                            result = await self._handle_generate_sql(session, result)
                        elif result.startswith("__CHART_DATA__"):
                            chart_json = self._extract_marker(result, "__CHART_DATA__", "__END_CHART_DATA__")
                            if chart_json:
                                try:
                                    chart_spec = json.loads(chart_json)
                                    yield ("chart", chart_spec)
                                    n = len(chart_spec.get("data", []))
                                    result = f"График «{chart_spec.get('title', '')}» отображён ({chart_spec.get('type', '')}, {n} точек данных)."
                                except json.JSONDecodeError:
                                    result = "Ошибка генерации графика."
                        elif result.startswith("__EXPORT_DATA__"):
                            export_info = self._extract_marker(result, "__EXPORT_DATA__", "__END_EXPORT_DATA__")
                            if export_info:
                                export_data = {}
                                for line in export_info.split("\n"):
                                    if "=" in line:
                                        k, v = line.split("=", 1)
                                        export_data[k] = v
                                yield ("export", export_data)
                                result = f"Файл {export_data.get('filename', '')} готов к скачиванию ({export_data.get('rows', '?')} строк)."
                        elif result.startswith("__DASHBOARD_CREATED__"):
                            dash_json = self._extract_marker(result, "__DASHBOARD_CREATED__", "__END_DASHBOARD_CREATED__")
                            if dash_json:
                                try:
                                    dash_info = json.loads(dash_json)
                                    yield ("dashboard", dash_info)
                                    result = f"Дашборд «{dash_info.get('title', '')}» создан! Ссылка: {dash_info.get('url', '')}"
                                except json.JSONDecodeError:
                                    result = "Ошибка создания дашборда."

                    except Exception as e:
                        result = f"Ошибка выполнения {func_name}: {e}"
                else:
                    result = f"Неизвестный инструмент: {func_name}"

                yield ("tool_result", func_name, result, tc_id)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": str(result),
                })

        if not hasattr(session, "_chat_history"):
            session._chat_history = []
        if not hasattr(session, "_pdf_log"):
            session._pdf_log = []

        session._chat_history.append({"role": "user", "content": user_message})

        last_content = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                last_content = msg["content"]
                break
        session._chat_history.append({"role": "assistant", "content": last_content})

        session._pdf_log.append({"role": "user", "content": user_message})

        pdf_answer_parts = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role == "assistant" and content:
                pdf_answer_parts.append(content)
            elif role == "tool" and content and not content.startswith("__"):
                clean = content.strip()
                if clean and len(clean) > 5:
                    pdf_answer_parts.append(clean)

        full_answer = "\n\n---\n\n".join(p for p in pdf_answer_parts if p and p.strip())
        if not full_answer.strip() and last_content:
            full_answer = last_content
        session._pdf_log.append({"role": "assistant", "content": full_answer})

        session._chat_history = self._compact_history(session._chat_history)

        yield ("done",)

    async def _stream_chat(
        self, messages: list[dict], tools: list[dict] | None
    ) -> AsyncGenerator[tuple, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": settings.llm_max_tokens,
            "temperature": settings.llm_temperature,
            "stream": True,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        url = f"{self.base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("POST", url, json=payload, headers=self._headers()) as resp:
                if resp.status_code != 200:
                    error_body = await resp.aread()
                    raise Exception(f"LLM API {resp.status_code}: {error_body.decode()}")

                tool_calls_accum: dict[int, dict] = {}

                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = data.get("choices", [])
                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})

                    if "content" in delta and delta["content"]:
                        yield ("content", delta["content"])

                    if "tool_calls" in delta:
                        for tc_delta in delta["tool_calls"]:
                            idx = tc_delta.get("index", 0)
                            if idx not in tool_calls_accum:
                                tool_calls_accum[idx] = {
                                    "id": tc_delta.get("id", f"call_{idx}"),
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                            if tc_delta.get("id"):
                                tool_calls_accum[idx]["id"] = tc_delta["id"]
                            if "function" in tc_delta:
                                fn = tc_delta["function"]
                                if "name" in fn:
                                    tool_calls_accum[idx]["function"]["name"] += fn["name"]
                                if "arguments" in fn:
                                    tool_calls_accum[idx]["function"]["arguments"] += fn["arguments"]

                if tool_calls_accum:
                    yield ("tool_calls", [tool_calls_accum[i] for i in sorted(tool_calls_accum)])

    async def _handle_classify(self, session: Session, task_data: str) -> str:
        lines = task_data.split("\n")
        params = {}
        data_json = ""
        for line in lines:
            if line == "__CLASSIFY_TASK__" or line == "__END_CLASSIFY_TASK__":
                continue
            if line.startswith("data="):
                data_json = line[5:]
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                params[key] = val

        import json as _json

        columns = _json.loads(params.get("columns", "[]"))
        categories = _json.loads(params.get("categories", "[]"))
        instruction = params.get("instruction", "")
        table_name = params.get("table_name", "")
        row_ids = _json.loads(params.get("row_ids", "[]"))
        data_rows = _json.loads(data_json) if data_json else []

        if not data_rows:
            return "Нет данных для классификации."

        from ..config import settings as cfg

        batch_size = cfg.classify_batch_size
        all_results = []

        for i in range(0, len(data_rows), batch_size):
            batch = data_rows[i : i + batch_size]
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
                        {"role": "user", "content": _json.dumps(batch_with_index, ensure_ascii=False, default=str)},
                    ]
                )
                try:
                    parsed = _json.loads(result)
                    if isinstance(parsed, list):
                        all_results.extend(parsed)
                except _json.JSONDecodeError:
                    all_results.append({"raw_response": result, "batch": i})
            except Exception as e:
                all_results.append({"error": str(e), "batch": i})

        if not all_results:
            return "Классификация не удалась."

        summary = {}
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

    async def _handle_generate_sql(self, session: Session, task_data: str) -> str:
        params = {}
        for line in task_data.split("\n"):
            if line.startswith("__GENERATE_SQL_TASK__") or line.startswith("__END_GENERATE_SQL_TASK__"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                if key in ("schema", "sample"):
                    params[key] = val
                else:
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

            import json as _json
            try:
                parsed = _json.loads(result)
                sql = parsed.get("sql", "")
                explanation = parsed.get("explanation", "")
            except _json.JSONDecodeError:
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

        except Exception as e:
            return f"Ошибка генерации SQL: {e}"

    @staticmethod
    def _extract_marker(text: str, start: str, end: str) -> str:
        s = text.find(start)
        e = text.find(end)
        if s >= 0 and e > s:
            return text[s + len(start):e].strip()
        return ""

    async def _single_completion(self, messages: list[dict]) -> str:
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

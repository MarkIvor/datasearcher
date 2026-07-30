from __future__ import annotations

import csv
import hashlib
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import settings
from .connectors import get_connector
from .connectors.base import Connector
from ..session import FileInfo, Session


_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return _ENV_REF.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def _safe_table_name(name: str) -> str:
    safe = re.sub(r"[^\w]", "_", name.strip(), flags=re.UNICODE)
    if safe and safe[0].isdigit():
        safe = f"t_{safe}"
    return safe or "table"


def _is_table_blocked(
    table_name: str,
    allowed_schemas: list[str] | None,
    blocked_patterns: list[str],
) -> bool:
    """Проверить, заблокирована ли таблица по schema ACL."""
    import fnmatch

    tn_lower = table_name.lower()

    for pattern in blocked_patterns:
        if fnmatch.fnmatch(tn_lower, pattern.lower()):
            return True

    if allowed_schemas:
        schema = ""
        if "." in table_name:
            schema = table_name.split(".")[0].lower()
        if schema and schema not in [s.lower() for s in allowed_schemas]:
            return True

    return False


@dataclass
class TableRef:
    """Ссылка на таблицу: может быть в source DB и/или DuckDB."""

    name: str
    table_name: str  # safe DuckDB-имя
    columns: list[dict]
    row_count: int
    source: str
    connector_name: str = ""
    in_duckdb: bool = False
    file_type: str = "table"
    csv_path: str = ""
    foreign_keys: list[dict] = field(default_factory=list)
    federated_alias: str = ""

    def to_file_info(self) -> FileInfo:
        return FileInfo(
            id=f"src_{self.table_name}",
            name=self.name,
            table_name=self.table_name,
            file_type=self.file_type,
            csv_path=self.csv_path,
            row_count=self.row_count,
            columns=self.columns,
        )


class AnalysisEngine:
    """Движок анализа, привязанный к web-сессии.

    Хранит коннекторы и метаданные таблиц для конкретной сессии DuckDB.
    Поддерживает режимы: remote (push-down), dump, auto, federated.
    """

    def __init__(self, session: Session):
        self.session = session
        self.connectors: dict[str, Connector] = {}
        self.tables: dict[str, TableRef] = {}
        self.connection_configs: list[dict] = []
        self._load_errors: list[str] = []
        self._ml_cache: dict[str, str] = {}

    @property
    def duckdb_enabled(self) -> bool:
        return True  # в web DuckDB-сессия всегда есть

    # ── Подключения ─────────────────────────────
    def load_from_connector(self, conn_cfg: dict) -> tuple[int, list[str]]:
        cfg = _expand_env(conn_cfg)
        name = cfg.get("name", cfg.get("db_type", "db"))
        db_type = cfg.get("db_type", "")
        mode = (cfg.get("mode") or settings.default_mode or "auto").lower()
        max_tables = int(cfg.get("max_tables", 30))
        max_rows = int(cfg.get("max_rows", 50000))

        try:
            connector = get_connector(name, db_type, cfg)
        except Exception as e:
            self._load_errors.append(f"{name}: {e}")
            return 0, [str(e)]

        self.connectors[name] = connector

        try:
            table_names = connector.list_tables()
        except Exception as e:
            self._load_errors.append(f"{name}: list_tables: {e}")
            return 0, [str(e)]

        added = 0
        errors: list[str] = []

        allowed_schemas = cfg.get("allowed_schemas") or cfg.get("schemas")
        if isinstance(allowed_schemas, str):
            allowed_schemas = [s.strip() for s in allowed_schemas.split(",") if s.strip()]
        blocked_patterns = cfg.get("blocked_tables")
        if isinstance(blocked_patterns, str):
            blocked_patterns = [p.strip() for p in blocked_patterns.split(",") if p.strip()]
        elif blocked_patterns is None:
            blocked_patterns = [p.strip() for p in settings.blocked_table_patterns.split(",") if p.strip()]

        from .knowledge_base import get_kb
        from .pii_detector import scan_table_for_pii
        kb = get_kb()

        for tbl in table_names[:max_tables]:
            if _is_table_blocked(tbl, allowed_schemas, blocked_patterns):
                continue

            safe = _safe_table_name(tbl)
            try:
                col_info = connector.describe(tbl)
                if not col_info:
                    cols, _ = connector.fetch_table(tbl, limit=1)
                    col_info = [{"name": c, "type": "unknown"} for c in cols]
                count = connector.row_count(tbl)
                fks = []
                try:
                    fks = connector.foreign_keys(tbl)
                except Exception:
                    pass

                kb.upsert_table(
                    table_name=safe,
                    connection=name,
                    source=f"{name} ({db_type})",
                )
                for col in col_info:
                    kb.upsert_column(safe, col["name"], source="schema")

                if settings.pii_masking:
                    try:
                        sample_cols, sample_rows = connector.fetch_table(tbl, limit=settings.pii_scan_rows)
                        if sample_rows:
                            scan_table_for_pii(safe, col_info, sample_rows)
                    except Exception:
                        pass

                ref = TableRef(
                    name=tbl,
                    table_name=safe,
                    columns=col_info,
                    row_count=count,
                    source=f"{name} ({db_type})",
                    connector_name=name,
                    in_duckdb=False,
                    file_type="db_view",
                    foreign_keys=fks,
                )
                self.tables[safe] = ref

                if mode == "dump":
                    if self._dump_table_to_duckdb(ref, connector, max_rows):
                        added += 1
                    else:
                        errors.append(f"{tbl}: dump failed")
                elif mode == "federated":
                    if self._attach_federated(ref, connector, name):
                        added += 1
                    else:
                        errors.append(f"{tbl}: federated attach failed")
                else:
                    # remote / auto — таблица доступна через push-down.
                    # Создаём FileInfo чтобы LLM видел таблицу в системном промпте,
                    # а данные выгружаются лениво при вызове ML-инструментов.
                    fi = ref.to_file_info()
                    self.session.files[fi.id] = fi
                    added += 1
            except Exception as e:
                errors.append(f"{tbl}: {e}")

        self.connection_configs.append(
            {"name": name, "db_type": db_type, "mode": mode, "tables_loaded": added}
        )

        from .logging_db import get_log_db
        get_log_db().log_audit(
            action="attach_database",
            target=name,
            details={"db_type": db_type, "mode": mode, "tables_loaded": added},
        )

        return added, errors

    def attach_connector(
        self, name: str, db_type: str, params: dict, mode: str = "auto"
    ) -> tuple[int, list[str]]:
        """Подключить новую БД в рантайме."""
        return self.load_from_connector(
            {"name": name, "db_type": db_type, "mode": mode, **params}
        )

    def get_connector_for_table(self, table_name: str) -> Connector | None:
        ref = self.tables.get(table_name)
        if ref and ref.connector_name:
            return self.connectors.get(ref.connector_name)
        return None

    def get_connector_by_name(self, name: str) -> Connector | None:
        return self.connectors.get(name)

    # ── Schema refresh ──────────────────────────
    def refresh_connector(self, name: str = "") -> tuple[int, list[str]]:
        """Обновить схему подключений (перечитать list_tables/describe/FK)."""
        if name and name not in self.connectors:
            return 0, [f"Подключение '{name}' не найдено"]
        targets = [name] if name else list(self.connectors.keys())
        added_total = 0
        errors: list[str] = []
        for conn_name in targets:
            connector = self.connectors[conn_name]
            try:
                table_names = connector.list_tables()
            except Exception as e:
                errors.append(f"{conn_name}: {e}")
                continue
            to_remove = [
                t for t, r in self.tables.items()
                if r.connector_name == conn_name and not r.in_duckdb
            ]
            for t in to_remove:
                self.tables.pop(t, None)
            for tbl in table_names:
                safe = _safe_table_name(tbl)
                if safe in self.tables:
                    try:
                        self.tables[safe].columns = connector.describe(tbl) or self.tables[safe].columns
                        self.tables[safe].row_count = connector.row_count(tbl)
                        self.tables[safe].foreign_keys = connector.foreign_keys(tbl)
                    except Exception:
                        pass
                    added_total += 1
                else:
                    try:
                        col_info = connector.describe(tbl)
                        count = connector.row_count(tbl)
                        fks = connector.foreign_keys(tbl)
                        self.tables[safe] = TableRef(
                            name=tbl, table_name=safe, columns=col_info,
                            row_count=count, source=f"{conn_name} ({connector.db_type})",
                            connector_name=conn_name, in_duckdb=False,
                            file_type="db_view", foreign_keys=fks,
                        )
                        added_total += 1
                    except Exception as e:
                        errors.append(f"{tbl}: {e}")

        from .logging_db import get_log_db
        get_log_db().log_audit(action="refresh_schema", target=name, details={"added": added_total})
        return added_total, errors

    # ── FK graph ────────────────────────────────
    def fk_graph(self) -> dict[str, list[dict]]:
        graph: dict[str, list[dict]] = {}
        for tname, ref in self.tables.items():
            if ref.foreign_keys:
                graph[tname] = ref.foreign_keys
        return graph

    def find_join_keys(self, table_a: str, table_b: str) -> list[tuple[str, str]]:
        keys: list[tuple[str, str]] = []
        ref_a = self.tables.get(table_a)
        ref_b = self.tables.get(table_b)
        if ref_a and ref_a.foreign_keys:
            for fk in ref_a.foreign_keys:
                if fk.get("ref_table") == ref_b.name if ref_b else False:
                    keys.append((fk["column"], fk.get("ref_column", "id")))
        if ref_b and ref_b.foreign_keys:
            for fk in ref_b.foreign_keys:
                if fk.get("ref_table") == ref_a.name if ref_a else False:
                    keys.append((fk.get("ref_column", "id"), fk["column"]))
        if not keys and ref_a and ref_b:
            cols_a = {c["name"].lower() for c in ref_a.columns}
            cols_b = {c["name"].lower() for c in ref_b.columns}
            common = cols_a & cols_b
            for c in common:
                if c.endswith("_id") or c == "id":
                    keys.append((c, c))
        if not keys and ref_a and ref_b:
            b_name = ref_b.name.lower().rstrip("s")
            for c in ref_a.columns:
                cn = c["name"].lower()
                if cn == f"{b_name}_id" or cn == f"{b_name}id":
                    keys.append((cn, "id"))
        return keys

    # ── SQL translation ─────────────────────────
    def translate_sql(self, sql: str, connector_name: str = "") -> str:
        """Перевести DuckDB SQL в диалект source DB через sqlglot."""
        if not settings.auto_translate:
            return sql
        connector = None
        if connector_name:
            connector = self.connectors.get(connector_name)
        if connector is None:
            connector = next(iter(self.connectors.values()), None)
        if connector is None:
            return sql
        target = connector.dialect()
        if target == "duckdb":
            return sql
        try:
            import sqlglot
            result = sqlglot.transpile(sql, read="duckdb", write=target)
            return result[0] if result else sql
        except Exception:
            return sql

    # ── Federated ──────────────────────────────
    def _attach_federated(self, ref: TableRef, connector: Connector, conn_name: str) -> bool:
        try:
            alias = f"fed_{conn_name}"
            if ref.federated_alias:
                return True
            attach_sql = connector.attach_duckdb_syntax(alias)
            self.session.conn.execute(attach_sql)
            for r in self.tables.values():
                if r.connector_name == conn_name:
                    r.federated_alias = alias
                    r.in_duckdb = True
            return True
        except Exception as e:
            self._load_errors.append(f"federated {conn_name}: {e}")
            return False

    def ensure_duckdb_extension(self, name: str) -> bool:
        try:
            conn = self.session.conn
            conn.execute(f"INSTALL {name}")
            conn.execute(f"LOAD {name}")
            return True
        except Exception:
            return False

    # ── Push-down (remote) ──────────────────────
    def execute_remote(self, sql: str, connector_name: str = "") -> tuple[list[str], list[tuple]]:
        """Выполнить SQL в source DB (push-down) с read-only guard и логированием."""
        from .sql_guard import check_read_only
        from .logging_db import get_log_db

        allowed, reason = check_read_only(sql)
        if not allowed:
            raise PermissionError(reason)

        connector = None
        if connector_name:
            connector = self.connectors.get(connector_name)
        if connector is None:
            connector = next(iter(self.connectors.values()), None)
        if connector is None:
            raise RuntimeError("Нет подключённых БД для remote-запроса")
        translated = self.translate_sql(sql, connector.name)

        import time
        start = time.time()
        try:
            cols, rows = connector.execute_sql(translated)
            duration_ms = int((time.time() - start) * 1000)

            get_log_db().log_query(
                tool="sql_query_remote",
                sql=sql[:500],
                connection=connector.name,
                rows_returned=len(rows),
                duration_ms=duration_ms,
                success=True,
            )

            # PII masking
            if settings.pii_masking and rows:
                from .pii_detector import mask_row, get_pii_columns_for_table
                # Определяем PII-колонки по именам в результате
                pii_cols: list[dict] = []
                # Ищем среди известных таблиц совпадение по колонкам
                for tname in self.tables:
                    pii_info = get_pii_columns_for_table(tname)
                    if pii_info:
                        pii_cols = pii_info
                        break
                if pii_cols:
                    cols_meta = [{"name": c} for c in cols]
                    rows = [mask_row(r, cols_meta, pii_cols) for r in rows]

            return cols, rows

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            error_msg = str(e)[:500]
            get_log_db().log_query(
                tool="sql_query_remote",
                sql=sql[:500],
                connection=connector.name,
                duration_ms=duration_ms,
                success=False,
                error=error_msg,
            )
            get_log_db().log_error(
                error_type="Remote SQL",
                message=error_msg,
                sql=sql[:500],
                connection=connector.name,
                tool="sql_query",
            )
            raise

    def has_remote_tables(self) -> bool:
        """Есть ли remote/auto-режим таблицы (требующие push-down)."""
        for ref in self.tables.values():
            if ref.connector_name and not ref.in_duckdb:
                return True
        return False

    # ── DuckDB dump ─────────────────────────────
    def _dump_table_to_duckdb(self, ref: TableRef, connector: Connector, max_rows: int) -> bool:
        try:
            cols, rows = connector.fetch_table(ref.name, limit=max_rows)
            if not cols:
                return False
            fi = self._load_rows_into_duckdb(ref.table_name, cols, rows)
            if fi:
                ref.in_duckdb = True
                ref.columns = fi.columns
                self.session.files[fi.id] = fi
                return True
        except Exception as e:
            self._load_errors.append(f"{ref.name}: dump: {e}")
        return False

    def _load_rows_into_duckdb(
        self, table_name: str, columns: list[str], rows: list[tuple]
    ) -> FileInfo | None:
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8"
        )
        try:
            writer = csv.writer(tmp)
            writer.writerow(columns)
            for row in rows:
                writer.writerow(["" if v is None else str(v) for v in row])
            tmp.close()

            for _ in range(2):
                try:
                    self.session.conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                except Exception:
                    pass
                try:
                    self.session.conn.execute(f'DROP VIEW IF EXISTS "{table_name}"')
                except Exception:
                    pass

            self.session.conn.execute(
                f'CREATE TABLE "{table_name}" AS '
                f"SELECT * FROM read_csv_auto('{tmp.name}', header=true, all_varchar=false, ignore_errors=true)"
            )
            desc = self.session.conn.execute(f'DESCRIBE "{table_name}"').fetchall()
            col_info = [{"name": r[0], "type": r[1]} for r in desc]
        except Exception as e:
            self._load_errors.append(f"{table_name}: {e}")
            return None
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

        fi = FileInfo(
            id=f"duck_{table_name}",
            name=table_name,
            table_name=table_name,
            file_type="db_view",
            csv_path="",
            row_count=len(rows),
            columns=col_info,
        )
        return fi

    def ensure_table_in_duckdb(
        self,
        table_name: str,
        columns: str = "",
        where: str = "",
        limit: int = 50000,
    ) -> str:
        """Гарантировать, что таблица (или подмножество колонок) загружена в DuckDB."""
        ref = self.tables.get(table_name)
        if ref is None:
            # Может уже в DuckDB (из CSV/Excel)
            existing_tables = {fi.table_name for fi in self.session.files.values()}
            if table_name in existing_tables:
                return table_name
            raise ValueError(f"Таблица '{table_name}' не найдена. Доступные: {sorted(self.tables.keys()) or sorted(existing_tables)}")

        if ref.in_duckdb and not columns:
            return ref.table_name

        connector = self.get_connector_for_table(table_name)
        if connector is None:
            raise RuntimeError(f"Нет коннектора для таблицы {table_name}")

        col_clause = ""
        if columns.strip():
            cols = [c.strip() for c in columns.split(",")]
            quoted = ", ".join(f'"{c}"' for c in cols)
            col_clause = quoted
        else:
            col_clause = "*"

        where_clause = f" WHERE {where}" if where.strip() else ""

        try:
            q = connector.quote(ref.name)
            if not columns:
                cols, rows = connector.fetch_table(ref.name, limit=limit)
            else:
                sql = f"SELECT {col_clause} FROM {q}{where_clause} LIMIT {limit}"
                cols, rows = connector.execute_sql(sql)

            if not cols:
                raise RuntimeError(f"Нет данных для таблицы {table_name}")

            duck_name = ref.table_name
            if columns.strip() and settings.ml_cache_enabled:
                hash_key = hashlib.md5(
                    f"{table_name}:{columns}:{where}:{limit}".encode()
                ).hexdigest()[:8]
                duck_name = f"_ml_{ref.table_name}_{hash_key}"
                if duck_name in self._ml_cache:
                    return self._ml_cache[duck_name]

            fi = self._load_rows_into_duckdb(duck_name, cols, rows)
            if fi:
                ref.columns = fi.columns
                ref.in_duckdb = True
                if duck_name != ref.table_name:
                    self._ml_cache[duck_name] = duck_name
                self.session.files[fi.id] = fi
                return duck_name
        except Exception as e:
            raise RuntimeError(f"Не удалось загрузить таблицу {table_name} в DuckDB: {e}")

        return ref.table_name

    # ── Загрузка файлов ─────────────────────────
    @staticmethod
    def _strip_bom(path: str) -> str:
        try:
            with open(path, "rb") as f:
                head = f.read(3)
            if head == b"\xef\xbb\xbf":
                with open(path, "rb") as f:
                    data = f.read()
                with open(path, "wb") as f:
                    f.write(data[3:])
        except Exception:
            pass
        return path

    def load_csv(self, path: str, table_name: str = "") -> FileInfo | None:
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            self._load_errors.append(f"Файл не найден: {path}")
            return None
        self._strip_bom(path)
        name = table_name or Path(path).stem
        safe = _safe_table_name(name)
        for attempt in ("auto", "explicit"):
            try:
                for _ in range(2):
                    try:
                        self.session.conn.execute(f'DROP TABLE IF EXISTS "{safe}"')
                    except Exception:
                        pass
                try:
                    self.session.conn.execute(f'DROP VIEW IF EXISTS "{safe}"')
                except Exception:
                    pass
                if attempt == "auto":
                    self.session.conn.execute(
                        f'CREATE TABLE "{safe}" AS '
                        f"SELECT * FROM read_csv_auto('{path}', header=true, all_varchar=false, ignore_errors=true)"
                    )
                else:
                    self.session.conn.execute(
                        f'CREATE TABLE "{safe}" AS '
                        f"SELECT * FROM read_csv('{path}', header=true, delim=',', all_varchar=false, ignore_errors=true)"
                    )
                break
            except Exception as e:
                if attempt == "explicit":
                    self._load_errors.append(f"{path}: {e}")
                    return None
        try:
            desc = self.session.conn.execute(f'DESCRIBE "{safe}"').fetchall()
            col_info = [{"name": r[0], "type": r[1]} for r in desc]
            count = self.session.conn.execute(f'SELECT COUNT(*) FROM "{safe}"').fetchone()[0]
        except Exception as e:
            self._load_errors.append(f"{path}: {e}")
            return None

        fi = FileInfo(
            id=f"file_{safe}", name=name, table_name=safe, file_type="csv",
            csv_path=path, row_count=count, columns=col_info,
        )
        self.session.files[fi.id] = fi
        self.tables[safe] = TableRef(
            name=name, table_name=safe, columns=col_info, row_count=count,
            source=path, in_duckdb=True, file_type="csv", csv_path=path,
        )
        return fi

    def load_excel(self, path: str, table_name: str = "", sheet: str = "") -> list[FileInfo]:
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            self._load_errors.append(f"Файл не найден: {path}")
            return []
        try:
            import pandas as pd
        except ImportError:
            self._load_errors.append("Для Excel нужен pandas/openpyxl")
            return []

        sheets_to_load = [sheet] if sheet else None
        if sheets_to_load is None:
            try:
                xl = pd.ExcelFile(path)
                sheets_to_load = xl.sheet_names
            except Exception as e:
                self._load_errors.append(f"{path}: {e}")
                return []

        results = []
        base_name = table_name or Path(path).stem
        for sh in sheets_to_load:
            try:
                df = pd.read_excel(path, sheet_name=sh)
            except Exception as e:
                self._load_errors.append(f"{path}:{sh}: {e}")
                continue
            tname = _safe_table_name(f"{base_name}_{sh}" if len(sheets_to_load) > 1 else base_name)
            cols = [str(c) for c in df.columns]
            rows = [tuple(None if pd.isna(v) else v for v in row) for row in df.itertuples(index=False, name=None)]
            fi = self._load_rows_into_duckdb(tname, cols, rows)
            if fi:
                ref = TableRef(
                    name=f"{base_name} ({sh})", table_name=tname, columns=fi.columns,
                    row_count=len(rows), source=f"{path}:{sh}", in_duckdb=True, file_type="xlsx",
                )
                self.tables[tname] = ref
                self.session.files[fi.id] = fi
                results.append(fi)
        return results

    def load_parquet(self, path: str, table_name: str = "") -> FileInfo | None:
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            self._load_errors.append(f"Файл не найден: {path}")
            return None
        name = table_name or Path(path).stem
        safe = _safe_table_name(name)
        try:
            for _ in range(2):
                try:
                    self.session.conn.execute(f'DROP TABLE IF EXISTS "{safe}"')
                except Exception:
                    pass
            self.session.conn.execute(
                f'CREATE TABLE "{safe}" AS SELECT * FROM read_parquet("{path}")'
            )
            desc = self.session.conn.execute(f'DESCRIBE "{safe}"').fetchall()
            col_info = [{"name": r[0], "type": r[1]} for r in desc]
            count = self.session.conn.execute(f'SELECT COUNT(*) FROM "{safe}"').fetchone()[0]
        except Exception as e:
            self._load_errors.append(f"{path}: {e}")
            return None

        fi = FileInfo(
            id=f"pq_{safe}", name=name, table_name=safe, file_type="parquet",
            csv_path=path, row_count=count, columns=col_info,
        )
        self.session.files[fi.id] = fi
        self.tables[safe] = TableRef(
            name=name, table_name=safe, columns=col_info, row_count=count,
            source=path, in_duckdb=True, file_type="parquet", csv_path=path,
        )
        return fi

    # ── Регистрация загруженных файлов ──────────
    def register_file_table(self, file_info: FileInfo):
        """Зарегистрировать таблицу из загруженного файла в engine.tables."""
        self.tables[file_info.table_name] = TableRef(
            name=file_info.name,
            table_name=file_info.table_name,
            columns=file_info.columns,
            row_count=file_info.row_count,
            source=file_info.csv_path or "upload",
            in_duckdb=True,
            file_type=file_info.file_type,
            csv_path=file_info.csv_path,
        )

    # ── Сервис ─────────────────────────────────
    def tables_summary(self) -> list[dict]:
        out = []
        for tname, ref in self.tables.items():
            out.append(
                {
                    "table_name": tname,
                    "name": ref.name,
                    "row_count": ref.row_count,
                    "columns": ref.columns,
                    "source": ref.source,
                    "file_type": ref.file_type,
                    "in_duckdb": ref.in_duckdb,
                    "connector": ref.connector_name,
                }
            )
        return out

    def errors(self) -> list[str]:
        return list(self._load_errors)

    def available_tables(self) -> set[str]:
        return set(self.tables.keys())

    def get_table_ref(self, table_name: str) -> TableRef | None:
        return self.tables.get(table_name)


def get_engine_for_session(session: Session) -> AnalysisEngine:
    """Получить (или создать) AnalysisEngine для web-сессии.

    Engine хранится на самом объекте сессии как `_engine`.
    """
    eng = getattr(session, "_engine", None)
    if eng is None:
        eng = AnalysisEngine(session)
        session._engine = eng
    # Синхронизировать уже загруженные файлы (могли добавиться после создания engine)
    for fi in session.files.values():
        if fi.table_name not in eng.tables:
            eng.register_file_table(fi)
    return eng
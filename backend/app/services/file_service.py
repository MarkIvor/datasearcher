from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import openpyxl

from ..config import settings
from ..session import FileInfo, Session


def detect_type(path: str) -> str:
    with open(path, "rb") as f:
        return "xlsx" if f.read(4) == b"PK\x03\x04" else "csv"


def xlsx_to_csv(xlsx_path: str) -> str:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
    )
    try:
        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
        ws = wb.active
        writer = csv.writer(tmp)
        for row in ws.iter_rows(values_only=True):
            writer.writerow([("" if v is None else v) for v in row])
        wb.close()
    finally:
        tmp.close()
    return tmp.name


def make_table_name(filename: str) -> str:
    name = Path(filename).stem
    name = name.replace(" ", "_").replace("-", "_").replace(".", "_")
    import re

    name = re.sub(r"[^a-zA-Z0-9_а-яА-ЯёЁ]", "_", name)
    if not name or name[0].isdigit():
        name = "t_" + name
    return name.lower()


def register_file(session: Session, file_path: str, filename: str) -> FileInfo:
    file_type = detect_type(file_path)

    if file_type == "xlsx":
        csv_path = xlsx_to_csv(file_path)
    else:
        csv_path = file_path

    table_name = make_table_name(filename)
    base_name = table_name
    counter = 1
    existing_names = {fi.table_name for fi in session.files.values()}
    while table_name in existing_names:
        table_name = f"{base_name}_{counter}"
        counter += 1

    session.conn.execute(
        f"CREATE VIEW \"{table_name}\" AS SELECT * FROM read_csv_auto('{csv_path}', header=true, ignore_errors=true, all_varchar=false, normalize_names=false)"
    )

    schema_rows = session.conn.execute(f'DESCRIBE "{table_name}"').fetchall()
    count = session.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]

    columns = [
        {"name": row[0], "type": row[1], "nullable": row[2] == "YES" if len(row) > 2 else True}
        for row in schema_rows
    ]

    file_id = __import__("uuid").uuid4().hex[:12]
    fi = FileInfo(
        id=file_id,
        name=filename,
        table_name=table_name,
        file_type=file_type,
        csv_path=csv_path,
        row_count=count,
        columns=columns,
    )
    session.files[file_id] = fi
    session.touch()
    return fi


def unregister_file(session: Session, file_id: str) -> bool:
    fi = session.files.pop(file_id, None)
    if not fi:
        return False
    try:
        session.conn.execute(f'DROP VIEW IF EXISTS "{fi.table_name}"')
    except Exception:
        pass
    try:
        Path(fi.csv_path).unlink(missing_ok=True)
    except Exception:
        pass
    session.touch()
    return True

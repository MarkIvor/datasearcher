from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from ..models import FileListResponse, FileUploadResponse

router = APIRouter(prefix="/api/files", tags=["files"])


def _get_or_create_session(request: Request):
    session_id = request.cookies.get("session_id")
    mgr = request.app.state.session_manager
    return mgr.get_or_create(session_id)


def _set_session_cookie(response: JSONResponse, session_id: str):
    response.set_cookie("session_id", session_id, max_age=86400, httponly=False)


@router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    session = _get_or_create_session(request)

    from ..config import settings

    content = await file.read()
    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            413, f"File too large (max {settings.max_file_size_mb} MB)"
        )

    if content[:3] == b"\xef\xbb\xbf":
        content = content[3:]

    suffix = Path(file.filename or "data.csv").suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(content)
        tmp.close()
        from ..services.file_service import register_file

        fi = register_file(session, tmp.name, file.filename or "data.csv")
    except Exception as e:
        try:
            Path(tmp.name).unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(400, f"Failed to process file: {e}")

    body = FileUploadResponse(
        file_id=fi.id,
        table_name=fi.table_name,
        file_type=fi.file_type,
        row_count=fi.row_count,
        columns=fi.columns,
    )
    resp = JSONResponse(content=body.model_dump())
    _set_session_cookie(resp, session.id)
    return resp


@router.get("/")
async def list_files(request: Request):
    session = _get_or_create_session(request)
    files = [
        FileUploadResponse(
            file_id=fi.id,
            table_name=fi.table_name,
            file_type=fi.file_type,
            row_count=fi.row_count,
            columns=fi.columns,
        )
        for fi in session.files.values()
    ]
    resp = JSONResponse(content=FileListResponse(files=files).model_dump())
    _set_session_cookie(resp, session.id)
    return resp


@router.delete("/{file_id}")
async def delete_file(request: Request, file_id: str):
    session = _get_or_create_session(request)
    from ..services.file_service import unregister_file

    if not unregister_file(session, file_id):
        raise HTTPException(404, "File not found")
    return {"ok": True}


@router.get("/{file_id}/preview")
async def preview_file(request: Request, file_id: str, rows: int = 50):
    session = _get_or_create_session(request)
    fi = session.files.get(file_id)
    if not fi:
        raise HTTPException(404, "File not found")

    rows = min(max(rows, 1), 200)
    conn = session.conn
    try:
        result = conn.execute(f'SELECT * FROM "{fi.table_name}" LIMIT {rows}')
        columns = [d[0] for d in result.description]
        data = result.fetchall()
    except Exception as e:
        raise HTTPException(400, f"Query error: {e}")

    import math
    from datetime import date, datetime

    def safe(v):
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

    resp_data = {
        "table_name": fi.table_name,
        "columns": columns,
        "rows": [[safe(cell) for cell in row] for row in data],
        "total_rows": fi.row_count,
    }
    resp = JSONResponse(content=resp_data)
    _set_session_cookie(resp, session.id)
    return resp

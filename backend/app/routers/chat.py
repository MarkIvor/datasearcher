from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse, FileResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..models import ChatRequest
from ..models.database import get_db, User
from ..services.llm_service import LLMService
from .auth import get_current_user, get_optional_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


class PDFExportRequest(BaseModel):
    charts: list[dict] = []
    title: str = "DataSearcher Report"


@router.post("/")
async def chat(request: Request, body: ChatRequest, user: User = Depends(get_optional_user), db: Session = Depends(get_db)):
    mgr = request.app.state.session_manager
    session_id = body.session_id or request.cookies.get("session_id")
    session = mgr.get_or_create(session_id)

    if user:
        llm_service = LLMService.from_user_settings(db, user.id)
    else:
        llm_service = request.app.state.llm_service

    session._user_id = user.id if user else None
    session._base_url = str(request.base_url).rstrip("/")

    async def event_stream():
        try:
            async for event in llm_service.chat(session, body.message):
                if await request.is_disconnected():
                    break
                if event[0] == "token":
                    yield f"event: token\ndata: {json.dumps({'content': event[1]}, ensure_ascii=False)}\n\n"
                elif event[0] == "tool_call":
                    yield f"event: tool_call\ndata: {json.dumps({'name': event[1], 'args': event[2], 'tool_call_id': event[3] if len(event) > 3 else ''}, ensure_ascii=False)}\n\n"
                elif event[0] == "tool_result":
                    yield f"event: tool_result\ndata: {json.dumps({'name': event[1], 'result': event[2], 'tool_call_id': event[3] if len(event) > 3 else ''}, ensure_ascii=False)}\n\n"
                elif event[0] == "chart":
                    yield f"event: chart\ndata: {json.dumps(event[1], ensure_ascii=False)}\n\n"
                elif event[0] == "step":
                    yield f"event: step\ndata: {json.dumps({'text': event[1]}, ensure_ascii=False)}\n\n"
                elif event[0] == "dashboard":
                    yield f"event: dashboard\ndata: {json.dumps(event[1], ensure_ascii=False)}\n\n"
                elif event[0] == "export":
                    yield f"event: export\ndata: {json.dumps(event[1], ensure_ascii=False)}\n\n"
                elif event[0] == "error":
                    yield f"event: error\ndata: {json.dumps({'error': event[1]}, ensure_ascii=False)}\n\n"
                elif event[0] == "done":
                    yield f"event: done\ndata: {{\"session_id\": \"{session.id}\"}}\n\n"
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            return
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    resp = StreamingResponse(event_stream(), media_type="text/event-stream")
    resp.set_cookie("session_id", session.id, max_age=86400)
    return resp


@router.get("/export/{export_id}")
async def download_export(request: Request, export_id: str):
    import os
    session_id = request.cookies.get("session_id")
    if not session_id:
        return {"error": "No session"}
    mgr = request.app.state.session_manager
    session = mgr.get_or_create(session_id)
    exports = getattr(session, "_exports", {})
    filepath = exports.get(export_id)
    if not filepath or not os.path.exists(filepath):
        return {"error": "Export not found"}
    filename = os.path.basename(filepath)
    return FileResponse(filepath, filename=filename, media_type="text/csv")


@router.get("/export-pdf")
async def export_pdf(request: Request):
    from ..services.pdf_export import generate_report_pdf

    session_id = request.cookies.get("session_id")
    if not session_id:
        return {"error": "No session"}
    mgr = request.app.state.session_manager
    session = mgr.get_or_create(session_id)
    chat_history = getattr(session, "_chat_history", [])

    if not chat_history:
        return {"error": "Нет данных для экспорта"}

    pdf_log = getattr(session, "_pdf_log", [])
    if not pdf_log:
        pdf_log = chat_history

    try:
        pdf_bytes = generate_report_pdf(pdf_log, charts=[], title="DataSearcher Report")
    except Exception as e:
        return {"error": f"Ошибка генерации PDF: {e}"}

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=datasearcher_report.pdf"},
    )


@router.post("/export-pdf")
async def export_pdf_with_charts(request: Request, body: PDFExportRequest):
    from ..services.pdf_export import generate_report_pdf

    session_id = request.cookies.get("session_id")
    if not session_id:
        return {"error": "No session"}
    mgr = request.app.state.session_manager
    session = mgr.get_or_create(session_id)
    chat_history = getattr(session, "_chat_history", [])

    pdf_log = getattr(session, "_pdf_log", [])
    if not pdf_log:
        pdf_log = chat_history

    try:
        pdf_bytes = generate_report_pdf(pdf_log, charts=body.charts, title=body.title)
    except Exception as e:
        return {"error": f"Ошибка генерации PDF: {e}"}

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=datasearcher_report.pdf"},
    )

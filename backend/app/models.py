from __future__ import annotations

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    file_id: str
    table_name: str
    file_type: str
    row_count: int
    columns: list[dict]


class FileListResponse(BaseModel):
    files: list[FileUploadResponse]


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ToolCallInfo(BaseModel):
    name: str
    args: dict
    result: str | None = None


class ChatMessage(BaseModel):
    role: str
    content: str | None = None
    tool_calls: list[ToolCallInfo] | None = None


class SessionResponse(BaseModel):
    session_id: str

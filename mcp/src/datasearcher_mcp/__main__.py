from __future__ import annotations

import argparse
import sys

from .config import settings
from .server import mcp


def main():
    parser = argparse.ArgumentParser(
        prog="datasearcher-mcp",
        description="DataSearcher MCP-сервер: аналитика данных и БД через DuckDB.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="Транспорт MCP (по умолчанию stdio).",
    )
    parser.add_argument(
        "--config",
        default=settings.connections_file,
        help="Путь к файлу подключений connections.yaml.",
    )
    parser.add_argument(
        "--host",
        default=settings.host,
        help="Хост для http/sse транспорта.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help="Порт для http/sse транспорта.",
    )
    parser.add_argument(
        "--auth-token",
        default=settings.auth_token,
        help="Bearer token для http/sse auth (B3). Пусто = без auth.",
    )
    args = parser.parse_args()

    # Переопределение настроек из CLI
    settings.connections_file = args.config
    settings.host = args.host
    settings.port = args.port
    settings.auth_token = args.auth_token

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport in ("http", "sse"):
        mcp.settings.host = args.host
        mcp.settings.port = args.port

        # B3: Auth middleware для HTTP/SSE
        if settings.auth_token:
            from starlette.middleware.base import BaseHTTPMiddleware
            from starlette.requests import Request
            from starlette.responses import JSONResponse

            class AuthMiddleware(BaseHTTPMiddleware):
                async def dispatch(self, request: Request, call_next):
                    auth = request.headers.get("Authorization", "")
                    token = settings.auth_token
                    if auth == f"Bearer {token}":
                        return await call_next(request)
                    # Проверяем query param для browser-friendly
                    if request.query_params.get("token") == token:
                        return await call_next(request)
                    return JSONResponse(
                        {"error": "Unauthorized", "hint": "Передайте Authorization: Bearer <token>"},
                        status_code=401,
                    )

            # FastMCP v1: доступ к starlette app через mcp.streamable_http_app / sse_app
            app_attr = "streamable_http_app" if args.transport == "http" else "sse_app"
            try:
                app = getattr(mcp, app_attr)
                app.add_middleware(AuthMiddleware)
            except AttributeError:
                # Fallback: пишем предупреждение
                import warnings
                warnings.warn(
                    "Auth middleware не удалось подключить. "
                    "Проверьте версию mcp SDK. Auth token игнорируется.",
                    stacklevel=2,
                )

        transport = "streamable-http" if args.transport == "http" else "sse"
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .models.database import init_db
from .routers import chat, files, settings as settings_router, auth, admin, connections, dashboards
from .services.llm_service import LLMService
from .session import SessionManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.session_manager = SessionManager(memory_limit=settings.duckdb_memory_limit)

    from .models.database import SessionLocal
    from .services.auth_service import get_app_setting
    db = SessionLocal()
    try:
        global_url = get_app_setting(db, "global_llm_url")
        global_key = get_app_setting(db, "global_llm_api_key")
        global_model = get_app_setting(db, "global_llm_model")
    finally:
        db.close()

    app.state.llm_service = LLMService(
        base_url=global_url or settings.llm_base_url,
        api_key=global_key or settings.llm_api_key,
        model=global_model or settings.llm_model,
    )

    async def cleanup_task():
        while True:
            await asyncio.sleep(300)
            app.state.session_manager.cleanup_expired(settings.session_ttl_minutes)

    task = asyncio.create_task(cleanup_task())
    yield
    task.cancel()


app = FastAPI(title="DataSearcher", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(connections.router)
app.include_router(dashboards.router)
app.include_router(files.router)
app.include_router(chat.router)
app.include_router(settings_router.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


import os
dist_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend_dist")
if os.path.isdir(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")

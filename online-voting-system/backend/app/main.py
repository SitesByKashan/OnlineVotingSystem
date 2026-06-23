from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import init_db
from .routes import admin, ai, auth, candidates, elections, notifications, votes, ws


def create_app() -> FastAPI:
    settings = get_settings()
    init_db()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin, "http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(candidates.router)
    app.include_router(elections.router)
    app.include_router(notifications.router)
    app.include_router(votes.router)
    app.include_router(admin.router)
    app.include_router(ai.router)
    app.include_router(ws.router)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "smartvote-api", "version": settings.app_version}

    return app


app = create_app()

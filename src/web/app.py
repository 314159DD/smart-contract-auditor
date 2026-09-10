"""
FastAPI application factory for the Contract Auditor API.

Start with:
  uvicorn src.web.app:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.web.routes import audit as audit_router
from src.web.routes import auth as auth_router
from src.web.routes import billing as billing_router
from src.web.routes import report as report_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="Smart Contract Auditor API",
        description="AI-powered Solidity security scanner — static analysis + Claude deep audit",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    import os
    is_production = os.getenv("APP_ENV") == "production"
    origins = [
        "https://smart-contract-auditor.vercel.app",
        "https://contractauditor.app",
    ]
    if not is_production:
        origins.append("http://localhost:3000")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https://smart-contract-auditor.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(audit_router.router)
    application.include_router(auth_router.router)
    application.include_router(billing_router.router)
    application.include_router(report_router.router)

    @application.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return application


app = create_app()

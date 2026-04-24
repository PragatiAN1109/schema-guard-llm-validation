"""
SchemaGuard — Production Backend

FastAPI application wired to the existing validation engine.
All core logic lives in the project root modules (validator/, rules/, drift/, scoring/).

Run:
    cd schema-guard-llm-validation
    uvicorn backend.app.main:app --reload --port 8000

Endpoints:
    GET  /api/health           — service status
    GET  /api/dashboard        — aggregated stats for frontend
    GET  /api/rules            — list all semantic rules
    GET  /api/examples         — curated sample records
    GET  /api/audit-logs       — validation history
    GET  /api/violations       — rule violation log
    POST /api/validate         — single record validation
    POST /api/batch-validate   — batch validation + drift
    POST /api/async/submit     — async job submission
    POST /api/async/process    — process async queue
    GET  /api/async/result/:id — fetch async result
    GET  /api/async/jobs       — list async jobs
    GET  /api/user/me          — authenticated user info
    GET  /api/user/stats       — per-user usage stats
"""

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import API_VERSION
from backend.app.routes.health import router as health_router
from backend.app.routes.validate import router as validate_router
from backend.app.routes.batch import router as batch_router
from backend.app.routes.async_jobs import router as async_router
from backend.app.routes.user import router as user_router
from backend.app.db.database import init_db

app = FastAPI(
    title="SchemaGuard",
    description="Semantic validation and drift detection for LLM-generated structured outputs.",
    version=API_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api", tags=["Health & Dashboard"])
app.include_router(validate_router, prefix="/api", tags=["Validation"])
app.include_router(batch_router, prefix="/api", tags=["Batch"])
app.include_router(async_router, prefix="/api/async", tags=["Async Pipeline"])
app.include_router(user_router, prefix="/api/user", tags=["User"])


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/")
def root():
    return {
        "service": "SchemaGuard",
        "version": API_VERSION,
        "api_docs": "/api/docs",
        "endpoints": [
            "GET  /api/health", "GET  /api/dashboard", "GET  /api/rules",
            "GET  /api/examples", "GET  /api/audit-logs", "GET  /api/violations",
            "POST /api/validate", "POST /api/batch-validate",
            "POST /api/async/submit", "POST /api/async/process",
            "GET  /api/async/result/{job_id}", "GET  /api/async/jobs",
        ],
    }

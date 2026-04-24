"""
SchemaGuard — FastAPI Application (Multi-User Platform)

Supports sync/async validation, token auth, per-user tracking, quotas.

Run:
    uvicorn api.main:app --reload --port 8000
"""

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes import router
from api.async_routes import async_router
from api.user_routes import user_router
from rag.api_routes import rag_router
from ingest.api_routes import ingest_router
from api.suggest_routes import suggest_router
from config import API_VERSION


app = FastAPI(
    title="SchemaGuard",
    description=(
        "Semantic compliance and drift detection for LLM-generated structured outputs. "
        "Multi-user platform with token auth, per-user quotas, usage tracking, and audit logging. "
        "Includes RAG-enhanced explanations and document ingest (PDF/text → JSON → validation)."
    ),
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(async_router,  prefix="/async",  tags=["Async Pipeline"])
app.include_router(user_router,   prefix="/user",   tags=["User & Analytics"])
app.include_router(rag_router,    prefix="/rag",    tags=["RAG Explanations"])
app.include_router(ingest_router, prefix="/ingest", tags=["Document Ingest"])
app.include_router(suggest_router, prefix="/suggest", tags=["Correction Suggestions"])


@app.get("/")
def root():
    return {
        "service": "SchemaGuard",
        "version": API_VERSION,
        "docs": "/docs",
        "auth": "Send Authorization: Bearer <api_key> header. Demo key: sg-key-demo-000",
        "endpoints": {
            "public":  ["/health", "/example"],
            "sync":    ["/validate", "/batch-validate"],
            "async":   ["/async/submit", "/async/submit-batch", "/async/process",
                        "/async/result/{job_id}", "/async/status/{job_id}",
                        "/async/jobs", "/async/metrics"],
            "user":    ["/user/me", "/user/stats", "/user/jobs", "/user/audit"],
            "rag":     [
                "GET  /rag/status   — check if FAISS index is built",
                "POST /rag/explain  — validate + RAG explanation",
                "POST /rag/search   — search knowledge base directly",
            ],
            "ingest":  [
                "GET  /ingest/supported-domains — list domains & file types",
                "POST /ingest/upload            — upload PDF/text → extract → validate",
            ],
            "suggestions": [
                "POST /suggest/suggest-fix      — validate + field-level corrections",
                "GET  /suggest/suggest-fix/rules — list rules with suggestion support",
            ],
        },
    }

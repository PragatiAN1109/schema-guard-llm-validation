"""
SchemaGuard RAG — /explain-with-rag endpoint
=============================================
Adds to the existing FastAPI app in api/routes.py.
Import this router in api/main.py with:

    from rag.api_routes import rag_router
    app.include_router(rag_router, prefix="/rag", tags=["RAG Explanations"])
"""

from __future__ import annotations
import os
import sys
import json
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

rag_router = APIRouter()


# ── request / response models ─────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    domain:  str  = Field(..., description="'healthcare_intake' or 'financial_loan_application'")
    record:  dict = Field(..., description="The JSON record that failed validation")
    record_id: Optional[str] = Field(None, description="Optional record ID for tracking")
    top_k:   int  = Field(3, ge=1, le=6, description="Number of context chunks to retrieve")


class ChunkRef(BaseModel):
    chunk_id:  str
    rule_id:   Optional[str]
    title:     str
    source:    str
    score:     float
    text_preview: str


class ExplainResponse(BaseModel):
    record_id:        str
    domain:           str
    decision:         str
    confidence_score: float
    violated_rules:   list[str]
    baseline_explanation:  str
    rag_explanation:       str
    retrieved_chunks:      list[ChunkRef]
    retrieval_query:  str
    latency_ms:       float


# ── helpers ───────────────────────────────────────────────────────────────────

def _resolve_domain(domain: str) -> str:
    from config import resolve_domain
    resolved = resolve_domain(domain)
    if not resolved:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown domain '{domain}'. Use: healthcare_intake or financial_loan_application"
        )
    return resolved


def _check_rag_ready() -> None:
    """Raise a clear error if the FAISS index hasn't been built yet."""
    from rag.vector_store import INDEX_PATH
    if not INDEX_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "RAG index not built. Run once from project root: "
                "python rag/vector_store.py --build"
            )
        )


def _check_api_key() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY not set. Required for RAG explanations."
        )


# ── endpoints ─────────────────────────────────────────────────────────────────

@rag_router.post("/explain", response_model=ExplainResponse)
def explain_with_rag(req: ExplainRequest):
    """
    Validate a record and return both a baseline and a RAG-augmented explanation.

    Steps:
      1. Run full validation pipeline
      2. Retrieve relevant knowledge-base chunks (FAISS)
      3. Call Claude with retrieved context to generate grounded explanation
      4. Return comparison: baseline vs RAG
    """
    _check_rag_ready()
    _check_api_key()

    domain = _resolve_domain(req.domain)

    # ── run validation ────────────────────────────────────────────────────────
    from validator.pipeline import validate_record
    val_result = validate_record(req.record, domain, record_id=req.record_id)

    if val_result["decision"] == "trusted" and not val_result["violated_rules"]:
        # Nothing to explain — return early
        return ExplainResponse(
            record_id         = val_result["record_id"],
            domain            = domain,
            decision          = val_result["decision"],
            confidence_score  = val_result["confidence_score"],
            violated_rules    = [],
            baseline_explanation  = val_result["explanation"],
            rag_explanation       = "No violations detected. Record passed all validation checks.",
            retrieved_chunks      = [],
            retrieval_query       = "",
            latency_ms            = 0.0,
        )

    violations = val_result.get("violated_rules", [])

    # ── RAG explanation ───────────────────────────────────────────────────────
    from rag.explainer import explain_with_rag as _rag_explain
    try:
        rag_result = _rag_explain(
            record    = req.record,
            domain    = domain,
            violations = violations,
            decision  = val_result["decision"],
            record_id = val_result["record_id"],
            top_k     = req.top_k,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG explanation failed: {str(e)}")

    # ── format response ───────────────────────────────────────────────────────
    chunk_refs = [
        ChunkRef(
            chunk_id     = c.chunk_id,
            rule_id      = c.rule_id,
            title        = c.title,
            source       = c.source,
            score        = round(c.score, 4),
            text_preview = c.text[:200] + "…",
        )
        for c in rag_result.retrieved_chunks
    ]

    return ExplainResponse(
        record_id         = rag_result.record_id,
        domain            = rag_result.domain,
        decision          = rag_result.decision,
        confidence_score  = val_result["confidence_score"],
        violated_rules    = rag_result.violated_rules,
        baseline_explanation  = rag_result.baseline,
        rag_explanation       = rag_result.rag_explanation,
        retrieved_chunks      = chunk_refs,
        retrieval_query       = rag_result.retrieval_query,
        latency_ms            = rag_result.latency_ms,
    )


@rag_router.get("/status")
def rag_status():
    """Check whether the RAG index is built and ready."""
    from rag.vector_store import INDEX_PATH, MANIFEST

    if not INDEX_PATH.exists():
        return {
            "ready": False,
            "message": "Index not built. Run: python rag/vector_store.py --build",
        }

    manifest = {}
    if MANIFEST.exists():
        import json
        with open(MANIFEST) as f:
            manifest = json.load(f)

    return {
        "ready":     True,
        "model":     manifest.get("model"),
        "n_chunks":  manifest.get("n_chunks"),
        "built_at":  manifest.get("built_at"),
    }


@rag_router.post("/search")
def search_knowledge_base(query: str, domain: str = None, top_k: int = 3):
    """
    Debug endpoint: search the knowledge base directly without running validation.
    Useful for inspecting what context would be retrieved for a given query.
    """
    _check_rag_ready()
    from rag.vector_store import RAGRetriever
    retriever = RAGRetriever()
    chunks = retriever.retrieve(query, top_k=top_k, domain_filter=domain)
    return {
        "query":   query,
        "results": [
            {
                "chunk_id": c["chunk_id"],
                "rule_id":  c.get("rule_id"),
                "title":    c["title"],
                "source":   c["source"],
                "score":    round(c["score"], 4),
                "preview":  c["text"][:300],
            }
            for c in chunks
        ],
    }

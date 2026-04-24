"""
SchemaGuard — Document Ingest API
====================================
POST /ingest/upload

Upload a PDF or text file, extract JSON fields with Claude,
and validate with SchemaGuard — all in one call.

Wire into api/main.py:
    from ingest.api_routes import ingest_router
    app.include_router(ingest_router, prefix="/ingest", tags=["Document Ingest"])
"""

from __future__ import annotations
import os
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

ingest_router = APIRouter()

_MAX_FILE_BYTES = 10 * 1024 * 1024   # 10 MB hard cap
_ALLOWED_EXT   = {".pdf", ".txt", ".md", ".text"}


def _check_api_key() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY not configured. Required for document extraction."
        )


@ingest_router.post("/upload")
async def upload_and_validate(
    file:   UploadFile = File(..., description="PDF or plain-text document"),
    domain: str        = Form(..., description="'healthcare_intake' or 'financial_loan_application'"),
):
    """
    Upload a document, extract structured fields with Claude, validate with SchemaGuard.

    Steps:
      1. Parse the uploaded file (PDF or UTF-8 text)
      2. Call Claude to extract domain-specific JSON fields
      3. Run SchemaGuard 4-stage validation pipeline
      4. Return extracted record + full validation result

    Supported file types: .pdf, .txt, .md
    Max file size: 10 MB
    """
    _check_api_key()

    # ── file guards ───────────────────────────────────────────────────────────
    from pathlib import Path
    filename  = file.filename or "upload"
    extension = Path(filename).suffix.lower()
    if extension not in _ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Allowed: {sorted(_ALLOWED_EXT)}"
        )

    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(raw) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(raw)//1024} KB). Max: {_MAX_FILE_BYTES//1024} KB."
        )

    # ── pipeline ──────────────────────────────────────────────────────────────
    try:
        from ingest.document_ingest import extract_and_validate
        result = extract_and_validate(raw, filename, domain)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    # ── serialise validation result (strip non-serialisable audit fields) ─────
    val = result.validation
    return {
        "filename":         result.filename,
        "domain":           result.domain,
        "extracted_text_preview": result.extracted_text[:400] + (
            "…" if len(result.extracted_text) > 400 else ""
        ),
        "extracted_record": result.extracted_record,
        "validation": {
            "record_id":        val.get("record_id"),
            "structural_valid": val.get("structural_valid"),
            "structural_errors":val.get("structural_errors", []),
            "semantic_valid":   val.get("semantic_valid"),
            "violated_rules":   val.get("violated_rules", []),
            "confidence_score": val.get("confidence_score"),
            "decision":         val.get("decision"),
            "explanation":      val.get("explanation"),
        },
        "ingest_latency_ms": result.latency_ms,
    }


@ingest_router.get("/supported-domains")
def supported_domains():
    """List the domains and file types supported by the ingest endpoint."""
    return {
        "domains": [
            {
                "id":    "healthcare_intake",
                "label": "Healthcare Intake",
                "description": "Patient intake forms, discharge summaries, clinical notes",
                "rules": ["HC-001", "HC-002", "HC-003", "HC-004", "HC-005"],
            },
            {
                "id":    "financial_loan_application",
                "label": "Financial Loan Application",
                "description": "Loan application forms, credit documents, financial statements",
                "rules": ["FN-001", "FN-002", "FN-003", "FN-004", "FN-005"],
            },
        ],
        "supported_file_types": sorted(_ALLOWED_EXT),
        "max_file_size_kb":     _MAX_FILE_BYTES // 1024,
    }

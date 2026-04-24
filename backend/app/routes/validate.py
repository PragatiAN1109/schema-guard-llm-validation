"""
Single-record validation route.
Delegates to the existing validator/pipeline.py engine.
Persists result + violations to SQLite.
"""

from fastapi import APIRouter, HTTPException
from backend.app.models.schemas import ValidateRequest, ValidationResponse
from backend.app.services.validation_service import validate_single
from backend.app.db.database import save_validation_run

router = APIRouter()


@router.post("/validate", response_model=ValidationResponse)
def validate(req: ValidateRequest):
    """Validate a single JSON record through the full pipeline."""
    try:
        result = validate_single(req.domain, req.record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {e}")

    # Attach input payload for audit persistence
    result["input_payload"] = req.record

    save_validation_run(result)

    return ValidationResponse(
        record_id=result["record_id"],
        domain=result["domain"],
        structural_valid=result["structural_valid"],
        structural_errors=result.get("structural_errors", []),
        semantic_valid=result["semantic_valid"],
        violated_rules=result.get("violated_rules", []),
        explanation=result.get("explanation", ""),
        confidence_score=result["confidence_score"],
        decision=result["decision"],
    )

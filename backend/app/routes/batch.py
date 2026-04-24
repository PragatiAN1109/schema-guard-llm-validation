"""
Batch validation route with drift detection.
Delegates to the existing validator/batch_validation.py engine.
"""

from fastapi import APIRouter, HTTPException
from backend.app.models.schemas import BatchValidateRequest, BatchValidationResponse
from backend.app.services.batch_service import validate_batch_records
from backend.app.db.database import save_batch_run

router = APIRouter()


@router.post("/batch-validate", response_model=BatchValidationResponse)
def batch_validate(req: BatchValidateRequest):
    """Validate multiple records with drift detection."""
    if len(req.records) == 0:
        raise HTTPException(status_code=400, detail="Records list is empty")
    if len(req.records) > 500:
        raise HTTPException(status_code=400, detail="Max 500 records per batch")

    try:
        result = validate_batch_records(req.domain, req.records)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch error: {e}")

    save_batch_run(result)

    return BatchValidationResponse(
        batch_id=result["batch_id"],
        domain=result["domain"],
        total_records=result["total_records"],
        results=result["results"],
        summary=result["summary"],
        drift_summary=result.get("drift_summary"),
    )

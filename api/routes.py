"""
SchemaGuard — API Routes

All endpoint handlers. Each route delegates to existing pipeline modules.
"""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

from api.models import (
    ValidateRequest, BatchValidateRequest, GenerateRequest,
    ValidationResponse, BatchValidationResponse, HealthResponse,
)
from validator.pipeline import validate_record
from validator.batch_validation import validate_batch
from config import resolve_domain, VALID_DOMAINS, API_VERSION


router = APIRouter()

SEED_DIR = Path(__file__).parent.parent / "data_gen" / "sample_data"


def _resolve(domain: str) -> str:
    resolved = resolve_domain(domain)
    if not resolved:
        raise HTTPException(status_code=400, detail=f"Unknown domain '{domain}'. Use: healthcare or finance")
    return resolved


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Service health check."""
    return {"status": "ok", "service": "SchemaGuard", "version": API_VERSION, "domains": VALID_DOMAINS}


@router.get("/example")
def get_example():
    """Return sample input payloads for both domains."""
    return {
        "healthcare_example": {
            "domain": "healthcare",
            "record": {
                "patient_id": "P-3021", "first_name": "James", "last_name": "Carter",
                "date_of_birth": "1978-11-02", "gender": "male",
                "admission_date": "2024-09-14", "discharge_date": "2024-09-19",
                "diagnosis_code": "J18.9",
                "diagnosis_description": "Pneumonia, unspecified organism",
                "treating_physician": "Dr. Susan Park", "medication": "Azithromycin",
                "procedure_code": None, "insurance_provider": "Aetna",
                "patient_age": 45, "emergency_admission": False, "notes": None,
            }
        },
        "finance_example": {
            "domain": "finance",
            "record": {
                "application_id": "LA-40821", "applicant_name": "Michael Torres",
                "date_of_birth": "1988-05-22", "annual_income": 92000,
                "employment_status": "employed", "employer_name": "Deloitte",
                "employment_length_years": 6, "loan_amount": 320000,
                "loan_purpose": "home_purchase", "loan_term_months": 360,
                "interest_rate": 6.75, "credit_score": 742, "existing_debt": 18000,
                "application_date": "2024-08-10", "approval_date": "2024-08-24",
                "approved_amount": 310000, "property_value": 415000,
                "co_applicant": False, "notes": None,
            }
        },
        "usage": "POST the healthcare_example or finance_example object to /validate",
    }


@router.post("/validate")
def validate_single(req: ValidateRequest):
    """Validate a single record against domain schema and semantic rules."""
    domain = _resolve(req.domain)

    try:
        result = validate_record(req.record, domain)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")

    return {
        "record_id": result["record_id"],
        "domain": result["domain"],
        "structural_valid": result["structural_valid"],
        "structural_errors": result.get("structural_errors", []),
        "semantic_valid": result["semantic_valid"],
        "violated_rules": result.get("violated_rules", []),
        "explanation": result.get("explanation", ""),
        "confidence_score": result["confidence_score"],
        "decision": result["decision"],
    }


@router.post("/batch-validate")
def validate_batch_endpoint(req: BatchValidateRequest):
    """Validate multiple records with drift detection."""
    domain = _resolve(req.domain)

    if len(req.records) == 0:
        raise HTTPException(status_code=400, detail="Records list is empty")
    if len(req.records) > 500:
        raise HTTPException(status_code=400, detail="Max 500 records per batch")

    try:
        batch_result = validate_batch(req.records, domain, run_drift=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch validation error: {str(e)}")

    simplified = []
    for r in batch_result["results"]:
        simplified.append({
            "record_id": r["record_id"],
            "structural_valid": r["structural_valid"],
            "semantic_valid": r["semantic_valid"],
            "violated_rules": r.get("violated_rules", []),
            "confidence_score": r["confidence_score"],
            "decision": r["decision"],
            "decision_reason": r.get("decision_reason", ""),
            "explanation": r.get("explanation", ""),
        })

    return {
        "batch_id": batch_result["batch_id"],
        "domain": domain,
        "total_records": batch_result["total_records"],
        "results": simplified,
        "summary": batch_result["summary"],
        "drift_summary": batch_result.get("drift_summary"),
    }


@router.post("/generate")
def generate_sample(req: GenerateRequest):
    """Return sample records from seed data."""
    domain = _resolve(req.domain)
    seed_file = "healthcare_seed_examples.json" if "healthcare" in domain else "finance_seed_examples.json"
    seed_path = SEED_DIR / seed_file

    if not seed_path.exists():
        raise HTTPException(status_code=404, detail=f"Seed data not found for domain: {domain}")

    with open(seed_path) as f:
        seeds = json.load(f)

    filtered = [s for s in seeds if s.get("category") == req.category]
    if not filtered:
        filtered = seeds

    samples = filtered[:req.count]
    return {
        "domain": domain,
        "category": req.category,
        "count": len(samples),
        "records": [{"record": s["record"], "label": s.get("category"), "notes": s.get("notes", "")} for s in samples],
    }

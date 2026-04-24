"""
Pydantic request/response models for the production backend API.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ── Requests ──

class ValidateRequest(BaseModel):
    domain: str = Field(..., description="Domain: 'healthcare', 'finance', or full name")
    record: dict = Field(..., description="JSON record to validate")


class BatchValidateRequest(BaseModel):
    domain: str
    records: list[dict]


# ── Responses ──

class ValidationResponse(BaseModel):
    record_id: str
    domain: str
    structural_valid: bool
    structural_errors: list[dict] = []
    semantic_valid: bool
    violated_rules: list[dict] = []
    explanation: str = ""
    confidence_score: float
    decision: str


class BatchSummary(BaseModel):
    trusted: int
    flagged: int
    quarantined: int
    mean_confidence: float
    processing_time_ms: float


class BatchValidationResponse(BaseModel):
    batch_id: str
    domain: str
    total_records: int
    results: list[dict]
    summary: dict
    drift_summary: Optional[dict] = None

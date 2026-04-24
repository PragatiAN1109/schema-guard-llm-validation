"""
SchemaGuard — API Request/Response Models

Pydantic models for all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Any, Optional


# --- Requests ---

class ValidateRequest(BaseModel):
    domain: str = Field(..., description="'healthcare_intake' or 'financial_loan_application'")
    record: dict = Field(..., description="JSON record to validate")


class BatchValidateRequest(BaseModel):
    domain: str = Field(..., description="'healthcare_intake' or 'financial_loan_application'")
    records: list[dict] = Field(..., description="List of JSON records to validate")


class GenerateRequest(BaseModel):
    domain: str = Field(default="healthcare_intake")
    category: str = Field(default="valid", description="'valid', 'invalid', or 'edge_case'")
    count: int = Field(default=1, ge=1, le=20)


# --- Responses ---

class RuleViolation(BaseModel):
    rule_id: str
    rule_name: str
    passed: bool
    severity: str
    fields: list[str]
    message: str


class ValidationResponse(BaseModel):
    record_id: str
    domain: str
    structural_valid: bool
    structural_errors: list[dict] = []
    semantic_valid: bool
    violated_rules: list[dict] = []
    explanation: str
    confidence_score: float
    decision: str


class BatchSummary(BaseModel):
    trusted: int
    flagged: int
    quarantined: int
    mean_confidence: float
    processing_time_ms: float


class DriftAlert(BaseModel):
    field: str
    type: str
    message: str
    severity: str


class DriftSummary(BaseModel):
    drift_detected: bool
    checked_fields: int
    alerts: list[dict] = []
    drift_metrics: dict = {}


class BatchValidationResponse(BaseModel):
    batch_id: str
    domain: str
    total_records: int
    results: list[dict]
    summary: BatchSummary
    drift_summary: Optional[dict] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    domains: list[str]


# ── Suggestion models ─────────────────────────────────────────────────────────

class SuggestFixRequest(BaseModel):
    domain: str = Field(..., description="'healthcare_intake' or 'financial_loan_application'")
    record: dict = Field(..., description="The original JSON record to validate and suggest fixes for")
    record_id: Optional[str] = Field(default=None, description="Optional record identifier")


class FieldCorrectionModel(BaseModel):
    field: str
    current_value: Optional[Any] = None
    suggested_value: Optional[Any] = None
    note: str = ""


class RuleSuggestionModel(BaseModel):
    rule_id: str
    rule_name: str
    severity: str
    violation_message: str
    explanation: str
    how_to_fix: str
    reference: str
    confidence: str   # "definite" | "probable" | "manual"
    field_corrections: list[FieldCorrectionModel] = []


class SuggestFixResponse(BaseModel):
    record_id: str
    domain: str
    decision: str
    confidence_score: float
    violated_rules: list[str]
    suggestions: list[RuleSuggestionModel]
    fixed_record: dict
    summary: str
    total_fixable: int
    total_manual: int

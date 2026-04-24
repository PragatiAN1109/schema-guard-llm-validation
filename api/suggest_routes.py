"""
SchemaGuard — Correction Suggestion API Routes

POST /suggest-fix
    Validate a record and return field-level correction suggestions
    for every violated rule.

Wire into api/main.py:
    from api.suggest_routes import suggest_router
    app.include_router(suggest_router, tags=["Correction Suggestions"])
"""
from __future__ import annotations

from dataclasses import asdict
from fastapi import APIRouter, HTTPException

from api.models import SuggestFixRequest, SuggestFixResponse, RuleSuggestionModel, FieldCorrectionModel
from config import resolve_domain
from validator.pipeline import validate_record
from suggestions.engine import suggest_fixes

suggest_router = APIRouter()


def _to_field_correction(fc) -> FieldCorrectionModel:
    return FieldCorrectionModel(
        field=fc.field,
        current_value=fc.current_value,
        suggested_value=fc.suggested_value,
        note=fc.note,
    )


def _to_rule_suggestion(s) -> RuleSuggestionModel:
    return RuleSuggestionModel(
        rule_id=s.rule_id,
        rule_name=s.rule_name,
        severity=s.severity,
        violation_message=s.violation_message,
        explanation=s.explanation,
        how_to_fix=s.how_to_fix,
        reference=s.reference,
        confidence=s.confidence,
        field_corrections=[_to_field_correction(fc) for fc in s.field_corrections],
    )


@suggest_router.post("/suggest-fix", response_model=SuggestFixResponse, tags=["Correction Suggestions"])
def suggest_fix(req: SuggestFixRequest):
    """
    Validate a record and return field-level correction suggestions.

    For each violated rule the response includes:
    - **explanation** — plain-English reason why the rule failed
    - **how_to_fix** — step-by-step remediation instruction
    - **field_corrections** — exact field → suggested value mappings
    - **confidence** — 'definite' (auto-computable), 'probable', or 'manual'
    - **reference** — regulation or clinical standard being enforced

    The response also includes a **fixed_record** with all *definite*
    corrections already applied, ready to resubmit for validation.
    """
    domain = resolve_domain(req.domain)
    if not domain:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown domain '{req.domain}'. Use 'healthcare_intake' or 'financial_loan_application'.",
        )

    # Step 1 — validate
    val = validate_record(
        req.record,
        domain,
        record_id=req.record_id or None,
    )

    # Step 2 — generate suggestions for every violated rule
    result = suggest_fixes(
        record=req.record,
        domain=domain,
        violated_rules=val["violated_rules"],
        record_id=val["record_id"],
    )

    return SuggestFixResponse(
        record_id=val["record_id"],
        domain=domain,
        decision=val["decision"],
        confidence_score=val["confidence_score"],
        violated_rules=[v["rule_id"] for v in val["violated_rules"]],
        suggestions=[_to_rule_suggestion(s) for s in result.suggestions],
        fixed_record=result.fixed_record,
        summary=result.summary,
        total_fixable=result.total_fixable,
        total_manual=result.total_manual,
    )


@suggest_router.get("/suggest-fix/rules", tags=["Correction Suggestions"])
def list_supported_rules():
    """List all rules that have correction suggestion support."""
    return {
        "supported_rules": {
            "healthcare_intake": [
                {"rule_id": "HC-001", "name": "age_matches_dates",
                 "severity": "critical", "confidence": "definite",
                 "description": "Computes correct patient_age from date_of_birth + admission_date"},
                {"rule_id": "HC-002", "name": "admission_after_birth",
                 "severity": "critical", "confidence": "manual",
                 "description": "Identifies whether DOB or admission_date is erroneous"},
                {"rule_id": "HC-003", "name": "discharge_after_admission",
                 "severity": "critical", "confidence": "probable",
                 "description": "Detects date swap vs genuine error; suggests corrected discharge_date"},
                {"rule_id": "HC-004", "name": "age_appropriate_diagnosis",
                 "severity": "warning", "confidence": "manual",
                 "description": "Flags age-restricted ICD-10 code; lists valid alternatives"},
                {"rule_id": "HC-005", "name": "medication_plausibility",
                 "severity": "warning", "confidence": "probable",
                 "description": "Suggests first-line medications for the diagnosis category"},
            ],
            "financial_loan_application": [
                {"rule_id": "FN-001", "name": "approval_after_application",
                 "severity": "critical", "confidence": "probable",
                 "description": "Detects date transposition; suggests corrected approval_date"},
                {"rule_id": "FN-002", "name": "loan_to_income_ratio",
                 "severity": "critical", "confidence": "definite",
                 "description": "Computes maximum allowable loan_amount at 10× income"},
                {"rule_id": "FN-003", "name": "debt_to_income_ratio",
                 "severity": "warning", "confidence": "probable",
                 "description": "Computes maximum existing_debt at 60% DTI; flags for manual review"},
                {"rule_id": "FN-004", "name": "employment_length_vs_age",
                 "severity": "critical", "confidence": "definite",
                 "description": "Computes max possible employment_length_years from applicant age"},
                {"rule_id": "FN-005", "name": "approved_within_requested",
                 "severity": "critical", "confidence": "definite",
                 "description": "Sets approved_amount to loan_amount; notes counter-offer requirement"},
            ],
        },
        "confidence_levels": {
            "definite": "Exact correct value computed from the record — safe to auto-apply",
            "probable": "Strongly guided recommendation — human confirmation advised before applying",
            "manual":   "System cannot derive the correct value — requires source-document verification",
        },
    }

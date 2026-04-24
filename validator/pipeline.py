"""
SchemaGuard — Validation Pipeline

Orchestrates the full per-record validation flow:
    structural → semantic → scoring → routing → explanation → audit

Hardened with edge-case handling, logging, and consistent error formats.
"""

import time
import uuid
from validator.structural import validate_structure
from validator.semantic import validate_semantics
from validator.explanation import build_explanation
from validator.audit import create_audit_entry, write_audit_log
from scoring.confidence import compute_confidence
from scoring.router import route_decision
from config import resolve_domain, VALID_DOMAINS
from utils.logger import get_logger, log_validation, log_rule_failure
from utils.errors import ValidationInputError, DomainError, format_error


logger = get_logger("validator.pipeline")


def validate_record(record, domain: str, record_id: str = None) -> dict:
    """
    Run the full validation pipeline on a single record.

    Handles:
        - Non-dict input (returns structural failure)
        - Unknown domain (returns error result)
        - None/empty record (returns structural failure)
        - Exceptions during rule execution (caught per-rule)

    Returns:
        Complete validation result dict. Never raises.
    """
    start = time.perf_counter()

    if record_id is None:
        prefix = "HC" if domain and "healthcare" in str(domain) else "FN"
        record_id = f"{prefix}-val-{uuid.uuid4().hex[:6]}"

    # Guard: resolve domain
    resolved_domain = resolve_domain(domain) if domain else None
    if resolved_domain is None:
        return _error_result(record_id, domain or "unknown", "Unknown domain", start)

    # Guard: record must be a non-empty dict
    if not isinstance(record, dict):
        return _error_result(record_id, resolved_domain, f"Record must be a JSON object, got {type(record).__name__}", start)
    if not record:
        return _error_result(record_id, resolved_domain, "Record is empty", start)

    try:
        # Step 1: Structural validation
        structural = validate_structure(record, resolved_domain)

        # Step 2: Semantic validation (only if structurally valid)
        if structural["valid"]:
            semantic = validate_semantics(record, resolved_domain)
        else:
            semantic = {
                "valid": False,
                "rules_evaluated": 0,
                "violations": [],
                "all_results": [],
            }

        # Step 3: Confidence scoring
        confidence = compute_confidence(structural, semantic)

        # Step 4: Routing decision
        decision = route_decision(confidence)

        # Step 5: Build explanation
        explanation = build_explanation(structural, semantic, decision, record_id)

        # Log result
        log_validation(logger, record_id, structural["valid"], semantic["valid"], confidence, decision)
        for v in semantic.get("violations", []):
            log_rule_failure(logger, record_id, v["rule_id"], v["rule_name"], v["severity"], v["message"])

        # Step 6: Audit log
        elapsed_ms = (time.perf_counter() - start) * 1000
        audit_entry = create_audit_entry(
            record_id=record_id,
            domain=resolved_domain,
            structural_result=structural,
            semantic_result=semantic,
            confidence_score=confidence,
            decision=decision,
            processing_time_ms=elapsed_ms,
        )
        write_audit_log(audit_entry)

        return {
            "record_id": record_id,
            "domain": resolved_domain,
            "structural_valid": structural["valid"],
            "structural_errors": structural.get("errors", []),
            "semantic_valid": semantic["valid"],
            "violated_rules": semantic.get("violations", []),
            "all_rule_results": semantic.get("all_results", []),
            "explanation": explanation,
            "confidence_score": round(confidence, 4),
            "decision": decision,
            "audit_entry": audit_entry,
        }

    except Exception as e:
        logger.error(f"[{record_id}] Pipeline error: {type(e).__name__}: {e}")
        return _error_result(record_id, resolved_domain, f"Internal error: {str(e)}", start)


def _error_result(record_id: str, domain: str, message: str, start_time: float) -> dict:
    """Return a safe error result that matches the normal output schema."""
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return {
        "record_id": record_id,
        "domain": domain,
        "structural_valid": False,
        "structural_errors": [{"field": "(root)", "message": message}],
        "semantic_valid": False,
        "violated_rules": [],
        "all_rule_results": [],
        "explanation": f"Record {record_id}: Validation failed. {message}. Quarantined.",
        "confidence_score": 0.0,
        "decision": "quarantined",
        "audit_entry": {
            "record_id": record_id,
            "domain": domain,
            "error": message,
            "processing_time_ms": round(elapsed_ms, 2),
        },
    }

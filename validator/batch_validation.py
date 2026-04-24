"""
SchemaGuard — Batch Validation (Hardened)

Validates a list of records with edge-case protection, logging,
and minimum-sample-size checks for drift detection.
"""

import time
import uuid
from validator.structural import validate_structure
from validator.semantic import validate_semantics
from validator.explanation import build_explanation
from scoring.confidence_score import compute_confidence_score
from scoring.decision import make_decision
from drift.drift_detector import run_drift_detection
from config import resolve_domain, MAX_BATCH_SIZE, DRIFT_MIN_SAMPLE_SIZE
from utils.logger import get_logger
from utils.errors import format_error


logger = get_logger("validator.batch")


def validate_batch(records, domain: str, run_drift: bool = True) -> dict:
    """
    Validate a batch of records end-to-end.

    Handles:
        - None or non-list input
        - Empty batch
        - Non-dict records within batch (skipped with error result)
        - Drift skipped if batch too small for statistical significance
    """
    start = time.perf_counter()
    batch_id = f"batch-{uuid.uuid4().hex[:8]}"

    # Guard: input type
    if not isinstance(records, list):
        return _empty_batch_result(batch_id, domain, "Input must be a list of records", start)
    if len(records) == 0:
        return _empty_batch_result(batch_id, domain, "Batch is empty", start)

    resolved = resolve_domain(domain)
    if resolved is None:
        return _empty_batch_result(batch_id, domain or "unknown", f"Unknown domain: {domain}", start)

    results = []
    trusted = flagged = quarantined = 0
    total_confidence = 0.0

    for i, record in enumerate(records):
        prefix = "HC" if "healthcare" in resolved else "FN"
        record_id = f"{prefix}-batch-{batch_id[-6:]}-{i:03d}"

        # Guard: skip non-dict records
        if not isinstance(record, dict):
            results.append(_record_error(record_id, f"Record at index {i} is not a JSON object"))
            quarantined += 1
            continue

        try:
            structural = validate_structure(record, resolved)
            semantic = validate_semantics(record, resolved) if structural["valid"] else {
                "valid": False, "rules_evaluated": 0, "violations": [], "all_results": []
            }

            score_result = compute_confidence_score(structural, semantic)
            confidence = score_result["confidence_score"]

            decision_result = make_decision(
                confidence_score=confidence,
                structural_valid=structural["valid"],
                semantic_valid=semantic["valid"],
                violated_rules=semantic["violations"],
            )
            decision = decision_result["decision"]
            explanation = build_explanation(structural, semantic, decision, record_id)

            result = {
                "record_id": record_id,
                "structural_valid": structural["valid"],
                "semantic_valid": semantic["valid"],
                "violated_rules": semantic["violations"],
                "confidence_score": confidence,
                "confidence_breakdown": score_result["breakdown"],
                "decision": decision,
                "decision_reason": decision_result["reason"],
                "explanation": explanation,
            }
        except Exception as e:
            logger.error(f"[{record_id}] Error processing record: {e}")
            result = _record_error(record_id, str(e))
            decision = "quarantined"

        results.append(result)
        if decision == "trusted": trusted += 1
        elif decision == "flagged": flagged += 1
        else: quarantined += 1
        total_confidence += result.get("confidence_score", 0.0)

    elapsed_ms = (time.perf_counter() - start) * 1000
    n = len(records)

    output = {
        "batch_id": batch_id,
        "domain": resolved,
        "total_records": n,
        "results": results,
        "summary": {
            "trusted": trusted,
            "flagged": flagged,
            "quarantined": quarantined,
            "mean_confidence": round(total_confidence / n, 4) if n > 0 else 0.0,
            "processing_time_ms": round(elapsed_ms, 2),
        },
    }

    # Drift detection (skip if batch too small)
    if run_drift:
        if n < DRIFT_MIN_SAMPLE_SIZE:
            logger.info(f"[{batch_id}] Skipping drift detection: batch size {n} < minimum {DRIFT_MIN_SAMPLE_SIZE}")
            output["drift_summary"] = {
                "drift_detected": False,
                "checked_fields": 0,
                "drift_metrics": {},
                "alerts": [],
                "note": f"Batch too small for drift detection (n={n}, minimum={DRIFT_MIN_SAMPLE_SIZE})",
            }
        else:
            try:
                output["drift_summary"] = run_drift_detection(records, resolved, validation_results=results)
            except Exception as e:
                logger.error(f"[{batch_id}] Drift detection error: {e}")
                output["drift_summary"] = {"drift_detected": False, "error": str(e)}
    else:
        output["drift_summary"] = None

    logger.info(f"[{batch_id}] Batch complete: {n} records, T={trusted} F={flagged} Q={quarantined}, {elapsed_ms:.1f}ms")
    return output


def _empty_batch_result(batch_id, domain, message, start_time):
    return {
        "batch_id": batch_id,
        "domain": domain,
        "total_records": 0,
        "results": [],
        "summary": {"trusted": 0, "flagged": 0, "quarantined": 0, "mean_confidence": 0.0, "processing_time_ms": round((time.perf_counter() - start_time) * 1000, 2)},
        "drift_summary": None,
        "error": message,
    }


def _record_error(record_id, message):
    return {
        "record_id": record_id,
        "structural_valid": False,
        "semantic_valid": False,
        "violated_rules": [],
        "confidence_score": 0.0,
        "confidence_breakdown": {"base_score": 1.0, "structural_penalty": 1.0, "semantic_penalty": 0.0, "drift_penalty": 0.0, "sparse_penalty": 0.0},
        "decision": "quarantined",
        "decision_reason": f"Processing error: {message}",
        "explanation": f"Record {record_id}: Could not be validated. {message}. Quarantined.",
    }

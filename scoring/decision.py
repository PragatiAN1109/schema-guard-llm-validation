"""
SchemaGuard — Decision Router

Routes records to trusted / flagged / quarantined based on confidence
score and validation state. Provides detailed decision reasoning.

Thresholds:
    trusted:      confidence >= 0.85 AND structural_valid
    flagged:      0.50 <= confidence < 0.85 AND structural_valid
    quarantined:  confidence < 0.50 OR NOT structural_valid
"""

import os


# Configurable thresholds (override via environment)
TRUSTED_THRESHOLD = float(os.environ.get("CONFIDENCE_TRUSTED_THRESHOLD", "0.85"))
QUARANTINE_THRESHOLD = float(os.environ.get("CONFIDENCE_QUARANTINE_THRESHOLD", "0.50"))


def make_decision(
    confidence_score: float,
    structural_valid: bool,
    semantic_valid: bool,
    violated_rules: list = None,
) -> dict:
    """
    Make a routing decision for a validated record.

    Args:
        confidence_score: Float 0.0–1.0
        structural_valid: Whether schema validation passed
        semantic_valid: Whether all semantic rules passed
        violated_rules: List of rule violation dicts

    Returns:
        {
            "decision": "trusted" | "flagged" | "quarantined",
            "confidence_score": float,
            "reason": str,
            "thresholds": {"trusted": float, "quarantine": float},
        }
    """
    violated_rules = violated_rules or []
    has_critical = any(v.get("severity") == "critical" for v in violated_rules)

    # Quarantine: structural failure, very low confidence, or multiple critical violations
    if not structural_valid:
        return _result("quarantined", confidence_score, "Structural validation failed")

    if confidence_score < QUARANTINE_THRESHOLD:
        return _result("quarantined", confidence_score, f"Confidence ({confidence_score:.2f}) below quarantine threshold ({QUARANTINE_THRESHOLD})")

    if has_critical and confidence_score < TRUSTED_THRESHOLD:
        return _result("quarantined", confidence_score, "Critical rule violation with sub-trusted confidence")

    # Flagged: moderate confidence or non-critical violations
    if confidence_score < TRUSTED_THRESHOLD:
        return _result("flagged", confidence_score, f"Confidence ({confidence_score:.2f}) below trusted threshold ({TRUSTED_THRESHOLD})")

    if not semantic_valid:
        return _result("flagged", confidence_score, "Semantic violations detected despite high confidence")

    # Trusted
    return _result("trusted", confidence_score, "All checks passed")


def _result(decision: str, score: float, reason: str) -> dict:
    return {
        "decision": decision,
        "confidence_score": round(score, 4),
        "reason": reason,
        "thresholds": {
            "trusted": TRUSTED_THRESHOLD,
            "quarantine": QUARANTINE_THRESHOLD,
        },
    }

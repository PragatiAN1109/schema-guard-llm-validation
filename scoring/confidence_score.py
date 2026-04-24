"""
SchemaGuard — Confidence Scoring (Enhanced)

Computes a composite confidence score (0.0–1.0) from structural validation,
semantic validation, rule severity, and optional drift signals.

This module extends the base confidence.py with drift-aware scoring
and a more detailed breakdown.
"""

# Severity penalty weights
SEVERITY_PENALTIES = {
    "critical": 0.30,
    "warning": 0.12,
    "info": 0.05,
}

# Drift penalty (applied per alert in batch mode)
DRIFT_PENALTY_PER_ALERT = 0.03

# Structural failure penalty (immediate floor)
STRUCTURAL_FAILURE_SCORE = 0.0

# Sparse-evaluation penalty (no semantic rules ran)
SPARSE_PENALTY = 0.05


def compute_confidence_score(
    structural: dict,
    semantic: dict,
    drift_report: dict = None,
) -> dict:
    """
    Compute a detailed confidence score with breakdown.

    Args:
        structural: Output from validate_structure()
        semantic: Output from validate_semantics()
        drift_report: Optional drift detection report from run_drift_detection()

    Returns:
        {
            "confidence_score": float (0.0–1.0),
            "breakdown": {
                "base_score": 1.0,
                "structural_penalty": float,
                "semantic_penalty": float,
                "drift_penalty": float,
                "sparse_penalty": float,
            }
        }
    """
    breakdown = {
        "base_score": 1.0,
        "structural_penalty": 0.0,
        "semantic_penalty": 0.0,
        "drift_penalty": 0.0,
        "sparse_penalty": 0.0,
    }

    # Structural failure → immediate 0
    if not structural.get("valid", False):
        breakdown["structural_penalty"] = 1.0
        return {
            "confidence_score": STRUCTURAL_FAILURE_SCORE,
            "breakdown": breakdown,
        }

    score = 1.0

    # Semantic violations
    semantic_penalty = 0.0
    for violation in semantic.get("violations", []):
        severity = violation.get("severity", "warning")
        semantic_penalty += SEVERITY_PENALTIES.get(severity, 0.10)
    breakdown["semantic_penalty"] = round(semantic_penalty, 4)
    score -= semantic_penalty

    # Sparse evaluation penalty
    rules_evaluated = semantic.get("rules_evaluated", 0)
    if rules_evaluated == 0:
        breakdown["sparse_penalty"] = SPARSE_PENALTY
        score -= SPARSE_PENALTY

    # Drift penalty (batch mode only)
    if drift_report and drift_report.get("drift_detected", False):
        n_alerts = len(drift_report.get("alerts", []))
        drift_penalty = min(n_alerts * DRIFT_PENALTY_PER_ALERT, 0.15)  # cap at 0.15
        breakdown["drift_penalty"] = round(drift_penalty, 4)
        score -= drift_penalty

    final = max(0.0, min(1.0, round(score, 4)))

    return {
        "confidence_score": final,
        "breakdown": breakdown,
    }

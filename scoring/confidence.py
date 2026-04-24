"""
SchemaGuard — Confidence Scoring

Computes a composite confidence score (0.0–1.0) from structural
and semantic validation results.
"""

# Severity weights — how much each violation type reduces confidence
SEVERITY_WEIGHTS = {
    "critical": 0.30,
    "warning": 0.12,
    "info": 0.05,
}


def compute_confidence(structural: dict, semantic: dict) -> float:
    """
    Compute a confidence score for a validated record.

    Scoring logic:
        - Start at 1.0
        - If structurally invalid: immediately drop to 0.0
        - For each semantic violation: subtract based on severity weight
        - Clamp to [0.0, 1.0]

    Args:
        structural: Output from validate_structure()
        semantic: Output from validate_semantics()

    Returns:
        Float between 0.0 and 1.0
    """
    if not structural["valid"]:
        return 0.0

    score = 1.0

    for violation in semantic.get("violations", []):
        severity = violation.get("severity", "warning")
        penalty = SEVERITY_WEIGHTS.get(severity, 0.10)
        score -= penalty

    # Bonus: if all rules evaluated and all passed, no penalty
    # Mild penalty if very few rules could be evaluated (sparse record)
    rules_evaluated = semantic.get("rules_evaluated", 0)
    if rules_evaluated == 0 and structural["valid"]:
        score -= 0.05  # slight uncertainty when no semantic rules ran

    return max(0.0, min(1.0, round(score, 4)))

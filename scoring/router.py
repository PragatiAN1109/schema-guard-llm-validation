"""
SchemaGuard — Routing Logic

Routes records to trusted / flagged / quarantined based on confidence score.
"""

import os

# Thresholds — can be overridden via environment variables
TRUSTED_THRESHOLD = float(os.environ.get("CONFIDENCE_TRUSTED_THRESHOLD", "0.85"))
QUARANTINE_THRESHOLD = float(os.environ.get("CONFIDENCE_QUARANTINE_THRESHOLD", "0.50"))


def route_decision(confidence_score: float) -> str:
    """
    Route a record based on its confidence score.

    Returns:
        "trusted"     — confidence >= TRUSTED_THRESHOLD
        "flagged"     — QUARANTINE_THRESHOLD <= confidence < TRUSTED_THRESHOLD
        "quarantined" — confidence < QUARANTINE_THRESHOLD
    """
    if confidence_score >= TRUSTED_THRESHOLD:
        return "trusted"
    elif confidence_score >= QUARANTINE_THRESHOLD:
        return "flagged"
    else:
        return "quarantined"

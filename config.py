"""
SchemaGuard — Centralized Configuration

All configurable thresholds and parameters in one place.
Values can be overridden via environment variables.
"""

import os


# --- Scoring ---

CONFIDENCE_TRUSTED_THRESHOLD = float(os.environ.get("CONFIDENCE_TRUSTED_THRESHOLD", "0.85"))
CONFIDENCE_QUARANTINE_THRESHOLD = float(os.environ.get("CONFIDENCE_QUARANTINE_THRESHOLD", "0.50"))

SEVERITY_PENALTIES = {
    "critical": 0.30,
    "warning": 0.12,
    "info": 0.05,
}

DRIFT_PENALTY_PER_ALERT = 0.03
DRIFT_PENALTY_CAP = 0.15
SPARSE_EVALUATION_PENALTY = 0.05


# --- Drift Detection ---

DRIFT_NUMERIC_THRESHOLD = float(os.environ.get("DRIFT_NUMERIC_THRESHOLD", "1.5"))
DRIFT_CATEGORICAL_PSI_THRESHOLD = float(os.environ.get("DRIFT_CATEGORICAL_THRESHOLD", "0.20"))
DRIFT_NULL_RATE_THRESHOLD = float(os.environ.get("DRIFT_NULL_RATE_THRESHOLD", "0.15"))
DRIFT_VIOLATION_RATE_THRESHOLD = float(os.environ.get("DRIFT_VIOLATION_RATE_THRESHOLD", "0.10"))
DRIFT_MIN_SAMPLE_SIZE = int(os.environ.get("DRIFT_MIN_SAMPLE_SIZE", "5"))


# --- Domains ---

VALID_DOMAINS = ["healthcare_intake", "financial_loan_application"]

DOMAIN_ALIASES = {
    "healthcare": "healthcare_intake",
    "healthcare_intake": "healthcare_intake",
    "finance": "financial_loan_application",
    "financial": "financial_loan_application",
    "financial_loan_application": "financial_loan_application",
}


# --- API ---

API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8000"))
API_VERSION = "0.3.0"
MAX_BATCH_SIZE = 500


def resolve_domain(domain: str) -> str:
    """Resolve domain alias to canonical name. Returns None if unknown."""
    if not isinstance(domain, str):
        return None
    return DOMAIN_ALIASES.get(domain.lower().strip())

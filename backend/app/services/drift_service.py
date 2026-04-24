"""
Drift Service — wraps the existing drift/drift_detector.py engine.

Provides baseline management and drift detection as a service layer.
In production, drift detection would run as a scheduled batch job
(e.g., nightly cron via Airflow or AWS Step Functions).
"""

from config import resolve_domain
from drift.drift_detector import generate_baseline, run_drift_detection
from drift.baseline import load_baseline


def get_baseline(domain: str) -> dict:
    """Load the current baseline profile for a domain."""
    resolved = resolve_domain(domain)
    if resolved is None:
        raise ValueError(f"Unknown domain: '{domain}'")
    baseline = load_baseline(resolved)
    if baseline is None:
        return {"domain": resolved, "exists": False}
    return {"domain": resolved, "exists": True, "profile": baseline}


def create_baseline(domain: str, records: list[dict]) -> dict:
    """Generate a new baseline from the provided records."""
    resolved = resolve_domain(domain)
    if resolved is None:
        raise ValueError(f"Unknown domain: '{domain}'")
    profile = generate_baseline(records, resolved)
    return {"domain": resolved, "record_count": len(records), "fields": len(profile.get("fields", {}))}


def detect_drift(domain: str, records: list[dict]) -> dict:
    """Run drift detection against stored baseline."""
    resolved = resolve_domain(domain)
    if resolved is None:
        raise ValueError(f"Unknown domain: '{domain}'")
    return run_drift_detection(records, resolved)

"""
Batch Service — wraps the existing validator/batch_validation.py engine.

Handles domain resolution and delegates to the existing batch processor.
In production, this layer would integrate with Kafka consumers and
distributed worker pools.
"""

from config import resolve_domain
from validator.batch_validation import validate_batch
from drift.drift_detector import generate_baseline
from pathlib import Path
import json

SEED_DIR = Path(__file__).parent.parent.parent.parent / "data_gen" / "sample_data"
SEED_FILES = {
    "healthcare_intake": "healthcare_seed_examples.json",
    "financial_loan_application": "finance_seed_examples.json",
}


def validate_batch_records(domain: str, records: list[dict], run_drift: bool = True) -> dict:
    """
    Validate a batch of records with optional drift detection.

    Automatically generates a baseline from seed data if none exists.
    """
    resolved = resolve_domain(domain)
    if resolved is None:
        raise ValueError(f"Unknown domain: '{domain}'")

    # Auto-generate baseline from seed data if available
    _ensure_baseline(resolved)

    return validate_batch(records, resolved, run_drift=run_drift)


def _ensure_baseline(domain: str):
    """Generate drift baseline from seed data if not already present."""
    from drift.baseline import load_baseline
    if load_baseline(domain) is not None:
        return

    seed_file = SEED_FILES.get(domain)
    if not seed_file:
        return

    seed_path = SEED_DIR / seed_file
    if not seed_path.exists():
        return

    with open(seed_path) as f:
        seeds = json.load(f)

    valid_records = [s["record"] for s in seeds if s.get("category") == "valid"]
    if valid_records:
        generate_baseline(valid_records, domain)

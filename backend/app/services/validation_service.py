"""
Validation Service — wraps the existing validator/pipeline.py engine.

This is a thin adapter. All logic lives in the root-level validator/ package.
In production, this layer would add caching, metrics, and circuit breaking.
"""

from config import resolve_domain
from validator.pipeline import validate_record


def validate_single(domain: str, record: dict) -> dict:
    """
    Validate one record through the full pipeline.

    Args:
        domain: Domain name or alias (e.g., "healthcare", "finance")
        record: JSON record dict

    Returns:
        Full validation result dict from the existing pipeline.

    Raises:
        ValueError: If domain is unknown.
    """
    resolved = resolve_domain(domain)
    if resolved is None:
        raise ValueError(f"Unknown domain: '{domain}'")

    # Delegate to existing engine — no logic duplication
    return validate_record(record, resolved)

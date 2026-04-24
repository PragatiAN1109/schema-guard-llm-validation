"""
SchemaGuard — Structural Validator

Validates JSON records against their domain schema using jsonschema.
"""

import json
from pathlib import Path
from jsonschema import validate, ValidationError, Draft7Validator


SCHEMA_DIR = Path(__file__).parent.parent / "schemas"

_schema_cache: dict[str, dict] = {}

DOMAIN_SCHEMA_MAP = {
    "healthcare_intake": "healthcare_schema.json",
    "financial_loan_application": "finance_schema.json",
}


def load_schema(domain: str) -> dict:
    """Load and cache the JSON schema for a domain."""
    if domain in _schema_cache:
        return _schema_cache[domain]

    filename = DOMAIN_SCHEMA_MAP.get(domain)
    if not filename:
        raise ValueError(f"Unknown domain: {domain}")

    schema_path = SCHEMA_DIR / filename
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")

    with open(schema_path) as f:
        schema = json.load(f)

    _schema_cache[domain] = schema
    return schema


def validate_structure(record: dict, domain: str) -> dict:
    """
    Validate a record against the domain JSON schema.

    Returns:
        {
            "valid": bool,
            "errors": [
                {
                    "field": str,
                    "message": str,
                    "expected": str,
                    "actual": any,
                }
            ]
        }
    """
    schema = load_schema(domain)
    validator = Draft7Validator(schema)
    errors = []

    for error in sorted(validator.iter_errors(record), key=lambda e: list(e.absolute_path)):
        field = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append({
            "field": field,
            "message": error.message,
            "expected": str(error.schema),
            "actual": error.instance,
        })

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }

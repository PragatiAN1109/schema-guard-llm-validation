"""
SchemaGuard — Schema Validator

High-level interface for structural JSON schema validation.
Wraps the lower-level structural.py module with additional
error handling for malformed input.
"""

import json
from pathlib import Path
from validator.structural import validate_structure, load_schema, DOMAIN_SCHEMA_MAP


SUPPORTED_DOMAINS = list(DOMAIN_SCHEMA_MAP.keys())


def validate_schema(record, domain: str) -> dict:
    """
    Validate a record against its domain JSON schema.

    Handles:
        - Non-dict input
        - Raw JSON string input (auto-parsed)
        - Unknown domain names
        - Missing schema files

    Returns:
        {
            "structural_valid": bool,
            "errors": [...],
            "error_count": int,
            "domain": str,
        }
    """
    # Handle JSON string input
    if isinstance(record, str):
        try:
            record = json.loads(record)
        except json.JSONDecodeError as e:
            return {
                "structural_valid": False,
                "errors": [{
                    "field": "(root)",
                    "message": f"Invalid JSON: {str(e)}",
                    "expected": "valid JSON object",
                    "actual": record[:200] if len(record) > 200 else record,
                }],
                "error_count": 1,
                "domain": domain,
            }

    # Handle non-dict input
    if not isinstance(record, dict):
        return {
            "structural_valid": False,
            "errors": [{
                "field": "(root)",
                "message": f"Expected JSON object, got {type(record).__name__}",
                "expected": "object (dict)",
                "actual": str(record)[:200],
            }],
            "error_count": 1,
            "domain": domain,
        }

    # Validate domain
    if domain not in SUPPORTED_DOMAINS:
        return {
            "structural_valid": False,
            "errors": [{
                "field": "(root)",
                "message": f"Unknown domain '{domain}'. Supported: {SUPPORTED_DOMAINS}",
                "expected": "valid domain name",
                "actual": domain,
            }],
            "error_count": 1,
            "domain": domain,
        }

    # Run structural validation
    result = validate_structure(record, domain)

    return {
        "structural_valid": result["valid"],
        "errors": result["errors"],
        "error_count": len(result["errors"]),
        "domain": domain,
    }


def get_schema_info(domain: str) -> dict:
    """Return schema metadata for a domain."""
    schema = load_schema(domain)
    return {
        "domain": domain,
        "title": schema.get("title", ""),
        "required_fields": schema.get("required", []),
        "total_properties": len(schema.get("properties", {})),
        "allows_additional": schema.get("additionalProperties", True),
    }

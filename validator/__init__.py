"""
SchemaGuard — Validator Package

Core validation pipeline: structural → semantic → scoring → routing → explanation → audit
"""

from validator.pipeline import validate_record
from validator.schema_validator import validate_schema, get_schema_info
from validator.explanation import build_explanation, explain_single_violation

__all__ = [
    "validate_record",
    "validate_schema",
    "get_schema_info",
    "build_explanation",
    "explain_single_violation",
]

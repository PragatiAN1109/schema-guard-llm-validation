"""
SchemaGuard — Error Types

Standardized error format used across the API, validator, and drift modules.
Every error returned to the user follows this structure.
"""


class SchemaGuardError(Exception):
    """Base exception for SchemaGuard errors."""

    def __init__(self, message: str, error_type: str = "unknown", details: dict = None):
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "error": self.message,
            "type": self.error_type,
            "details": self.details,
        }


class ValidationInputError(SchemaGuardError):
    """Raised when input to the validator is malformed."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, error_type="validation_input_error", details=details)


class DomainError(SchemaGuardError):
    """Raised when an unknown domain is specified."""

    def __init__(self, domain: str):
        super().__init__(
            message=f"Unknown domain: '{domain}'",
            error_type="domain_error",
            details={"domain": domain, "valid_domains": ["healthcare_intake", "financial_loan_application"]},
        )


class SchemaLoadError(SchemaGuardError):
    """Raised when a schema file cannot be loaded."""

    def __init__(self, domain: str, path: str = None):
        super().__init__(
            message=f"Schema not found for domain: '{domain}'",
            error_type="schema_load_error",
            details={"domain": domain, "path": str(path) if path else None},
        )


class BaselineNotFoundError(SchemaGuardError):
    """Raised when drift detection is attempted without a baseline."""

    def __init__(self, domain: str):
        super().__init__(
            message=f"No baseline profile found for domain: '{domain}'. Generate one first.",
            error_type="baseline_not_found",
            details={"domain": domain},
        )


class BatchSizeError(SchemaGuardError):
    """Raised when batch size is invalid."""

    def __init__(self, size: int, max_size: int):
        super().__init__(
            message=f"Batch size {size} exceeds maximum {max_size}" if size > max_size else f"Batch is empty",
            error_type="batch_size_error",
            details={"size": size, "max_size": max_size},
        )


def format_error(message: str, error_type: str = "error", details: dict = None) -> dict:
    """Create a standardized error dict without raising an exception."""
    return {
        "error": message,
        "type": error_type,
        "details": details or {},
    }

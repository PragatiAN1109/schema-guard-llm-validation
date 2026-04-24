"""
SchemaGuard — Structured Logger

Provides consistent, readable logging across all modules.
Logs include timestamps, module names, and structured context.
"""

import logging
import sys
from datetime import datetime, timezone


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get a configured logger for a module.

    Args:
        name: Module name (e.g., "validator.pipeline", "drift.detector")
        level: Logging level (default: INFO)

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(f"schemaguard.{name}")

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False

    return logger


def log_validation(logger: logging.Logger, record_id: str, structural: bool, semantic: bool, confidence: float, decision: str):
    """Log a validation result in a consistent format."""
    status = "PASS" if (structural and semantic) else "FAIL"
    logger.info(
        f"[{record_id}] {status} | structural={'PASS' if structural else 'FAIL'} "
        f"semantic={'PASS' if semantic else 'FAIL'} | confidence={confidence:.2f} | decision={decision}"
    )


def log_rule_failure(logger: logging.Logger, record_id: str, rule_id: str, rule_name: str, severity: str, message: str):
    """Log a semantic rule violation."""
    logger.warning(f"[{record_id}] Rule {rule_id} ({rule_name}) [{severity}]: {message}")


def log_drift_alert(logger: logging.Logger, field: str, alert_type: str, severity: str, message: str):
    """Log a drift detection alert."""
    logger.warning(f"[DRIFT] {field} ({alert_type}) [{severity}]: {message}")


def log_error(logger: logging.Logger, context: str, error: Exception):
    """Log an error with context."""
    logger.error(f"[ERROR] {context}: {type(error).__name__}: {str(error)}")

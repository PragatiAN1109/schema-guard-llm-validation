"""
SchemaGuard — Audit Logger

Creates structured audit log entries for every validation run.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


AUDIT_LOG_DIR = Path(__file__).parent.parent / "audit_logs"


def create_audit_entry(
    record_id: str,
    domain: str,
    structural_result: dict,
    semantic_result: dict,
    confidence_score: float,
    decision: str,
    processing_time_ms: float,
) -> dict:
    """Build a structured audit log entry."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "record_id": record_id,
        "domain": domain,
        "structural_valid": structural_result["valid"],
        "structural_error_count": len(structural_result["errors"]),
        "semantic_valid": semantic_result["valid"],
        "rules_evaluated": [r["rule_id"] for r in semantic_result["all_results"]],
        "rules_violated": [r["rule_id"] for r in semantic_result["violations"]],
        "confidence_score": confidence_score,
        "decision": decision,
        "processing_time_ms": round(processing_time_ms, 2),
    }


def write_audit_log(entry: dict) -> None:
    """Append an audit entry to the domain-specific log file."""
    AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    domain = entry.get("domain", "unknown")
    log_path = AUDIT_LOG_DIR / f"{domain}_audit.jsonl"

    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

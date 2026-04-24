"""
Audit Service — retrieves validation audit logs from SQLite.
"""

from backend.app.db.database import get_audit_logs, get_violations


def get_audit(limit: int = 50, domain: str = None, decision: str = None) -> dict:
    """Return filtered audit log entries."""
    entries = get_audit_logs(limit=limit, domain=domain, decision=decision)
    return {"entries": entries, "count": len(entries)}


def get_violation_log(limit: int = 50, rule_id: str = None, domain: str = None) -> dict:
    """Return rule violations from the database."""
    violations = get_violations(limit=limit, rule_id=rule_id, domain=domain)
    return {"violations": violations, "count": len(violations)}

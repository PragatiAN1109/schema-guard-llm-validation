"""
Health, examples, rules, dashboard, and audit-log routes.
"""

from fastapi import APIRouter, Query
from typing import Optional
from config import API_VERSION, VALID_DOMAINS
from backend.app.services.dashboard_service import get_dashboard
from backend.app.services.rules_service import list_all_rules, get_rules_for_domain
from backend.app.services.examples_service import get_examples, get_example_by_category
from backend.app.services.audit_service import get_audit, get_violation_log

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "SchemaGuard",
        "version": API_VERSION,
        "domains": VALID_DOMAINS,
        "engine": "operational",
    }


@router.get("/dashboard")
def dashboard():
    """Aggregated dashboard data: counts, recent activity, top rules, per-domain stats."""
    return get_dashboard()


@router.get("/rules")
def rules(domain: Optional[str] = None):
    """List all semantic validation rules, optionally filtered by domain."""
    if domain:
        from config import resolve_domain
        resolved = resolve_domain(domain)
        if resolved:
            return {"domain": resolved, "rules": get_rules_for_domain(resolved)}
    return list_all_rules()


@router.get("/examples")
def examples(domain: Optional[str] = None, category: Optional[str] = None):
    """Return curated sample records for testing."""
    if domain:
        from config import resolve_domain
        resolved = resolve_domain(domain) or domain
        if category:
            return {"domain": resolved, "category": category, "examples": get_example_by_category(resolved, category)}
    return get_examples()


@router.get("/audit-logs")
def audit_logs(
    limit: int = Query(50, ge=1, le=500),
    domain: Optional[str] = None,
    decision: Optional[str] = None,
):
    """Retrieve validation audit log entries with optional filters."""
    return get_audit(limit=limit, domain=domain, decision=decision)


@router.get("/violations")
def violations(
    limit: int = Query(50, ge=1, le=500),
    rule_id: Optional[str] = None,
    domain: Optional[str] = None,
):
    """Retrieve rule violation records from the database."""
    return get_violation_log(limit=limit, rule_id=rule_id, domain=domain)

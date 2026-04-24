"""
User identity and stats routes.
Delegates to existing auth/ and analytics/ modules.
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from auth.auth import get_current_user
from analytics.usage_tracker import usage_tracker
from analytics.audit_log import audit_log
from storage.result_store import store
from backend.app.db.database import get_recent_validations

router = APIRouter()


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "role": user["role"],
        "quota_per_minute": user["quota_per_minute"],
    }


@router.get("/stats")
def stats(user: dict = Depends(get_current_user)):
    s = usage_tracker.get_user_stats(user["user_id"])
    if s is None:
        return {"user_id": user["user_id"], "total_requests": 0}
    return s


@router.get("/jobs")
def user_jobs(limit: int = 20, user: dict = Depends(get_current_user)):
    return {"jobs": store.list_jobs(user_id=user["user_id"], limit=limit)}


@router.get("/audit")
def user_audit(limit: int = 30, user: dict = Depends(get_current_user)):
    return {"entries": audit_log.get_user_entries(user["user_id"], limit=limit)}


@router.get("/history")
def user_history(limit: int = 20):
    """Return recent validation runs from SQLite (no auth required for demo)."""
    return {"validations": get_recent_validations(limit)}

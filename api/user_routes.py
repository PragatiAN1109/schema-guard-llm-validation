"""
SchemaGuard — User & Analytics Routes

Endpoints for user identity, usage stats, job history, and audit logs.
All endpoints require authentication.
"""

from fastapi import APIRouter, Depends, HTTPException

from auth.auth import get_current_user
from analytics.usage_tracker import usage_tracker
from analytics.audit_log import audit_log
from storage.result_store import store


user_router = APIRouter()


@user_router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    """Return the authenticated user's identity."""
    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "role": user["role"],
        "quota_per_minute": user["quota_per_minute"],
        "quota_remaining": usage_tracker.get_quota_remaining(user["user_id"], user["quota_per_minute"]),
    }


@user_router.get("/stats")
def get_user_stats(user: dict = Depends(get_current_user)):
    """Return the authenticated user's usage statistics."""
    stats = usage_tracker.get_user_stats(user["user_id"])
    if stats is None:
        return {
            "user_id": user["user_id"],
            "total_requests": 0,
            "succeeded": 0,
            "failed": 0,
            "success_rate": 0,
            "avg_confidence": 0,
            "decisions": {"trusted": 0, "flagged": 0, "quarantined": 0},
            "recent_jobs": [],
        }
    return stats


@user_router.get("/jobs")
def get_user_jobs(limit: int = 20, user: dict = Depends(get_current_user)):
    """List the authenticated user's jobs."""
    jobs = store.list_jobs(user_id=user["user_id"], limit=limit)
    return {"user_id": user["user_id"], "jobs": jobs, "count": len(jobs)}


@user_router.get("/audit")
def get_user_audit(limit: int = 30, user: dict = Depends(get_current_user)):
    """Return the authenticated user's audit log entries."""
    entries = audit_log.get_user_entries(user["user_id"], limit=limit)
    return {"user_id": user["user_id"], "entries": entries, "count": len(entries)}

"""
SchemaGuard — Per-User Usage Tracker

Tracks request counts, success/failure rates, and confidence scores per user.
Thread-safe. Designed for in-process analytics.

In production, replace with:
    - Redis sorted sets for real-time counters
    - ClickHouse/BigQuery for historical analytics
    - Stripe Metering for usage-based billing
"""

import time
import threading
from typing import Optional
from collections import defaultdict


class UsageTracker:
    """Per-user usage statistics."""

    def __init__(self):
        self._lock = threading.Lock()
        self._users: dict[str, dict] = defaultdict(self._blank_user)

    def _blank_user(self) -> dict:
        return {
            "total_requests": 0,
            "succeeded": 0,
            "failed": 0,
            "total_confidence": 0.0,
            "decisions": {"trusted": 0, "flagged": 0, "quarantined": 0},
            "first_seen": time.time(),
            "last_seen": time.time(),
            "recent_jobs": [],
        }

    def record_request(self, user_id: str, job_id: str, success: bool,
                       confidence: float = 0.0, decision: str = None):
        """Record a validation request for a user."""
        with self._lock:
            u = self._users[user_id]
            u["total_requests"] += 1
            u["last_seen"] = time.time()
            if success:
                u["succeeded"] += 1
                u["total_confidence"] += confidence
            else:
                u["failed"] += 1
            if decision and decision in u["decisions"]:
                u["decisions"][decision] += 1
            u["recent_jobs"].append({
                "job_id": job_id,
                "success": success,
                "confidence": confidence,
                "decision": decision,
                "timestamp": time.time(),
            })
            # Keep only last 50 jobs per user
            if len(u["recent_jobs"]) > 50:
                u["recent_jobs"] = u["recent_jobs"][-50:]

    def get_user_stats(self, user_id: str) -> Optional[dict]:
        """Return usage stats for a single user."""
        with self._lock:
            if user_id not in self._users:
                return None
            u = self._users[user_id]
            avg_conf = u["total_confidence"] / u["succeeded"] if u["succeeded"] > 0 else 0.0
            return {
                "user_id": user_id,
                "total_requests": u["total_requests"],
                "succeeded": u["succeeded"],
                "failed": u["failed"],
                "success_rate": round(u["succeeded"] / u["total_requests"], 4) if u["total_requests"] > 0 else 0,
                "avg_confidence": round(avg_conf, 4),
                "decisions": {**u["decisions"]},
                "first_seen": u["first_seen"],
                "last_seen": u["last_seen"],
                "recent_jobs": u["recent_jobs"][-10:],
            }

    def get_all_stats(self) -> dict:
        """Return stats for all users."""
        with self._lock:
            users = {}
            for uid, u in self._users.items():
                avg_conf = u["total_confidence"] / u["succeeded"] if u["succeeded"] > 0 else 0.0
                users[uid] = {
                    "total_requests": u["total_requests"],
                    "succeeded": u["succeeded"],
                    "failed": u["failed"],
                    "success_rate": round(u["succeeded"] / u["total_requests"], 4) if u["total_requests"] > 0 else 0,
                    "avg_confidence": round(avg_conf, 4),
                }
            return {"users": users, "total_users": len(users)}

    def check_quota(self, user_id: str, quota_per_minute: int) -> bool:
        """Check if user is within their per-minute quota. Returns True if allowed."""
        cutoff = time.time() - 60
        with self._lock:
            u = self._users.get(user_id)
            if u is None:
                return True
            recent = [j for j in u["recent_jobs"] if j["timestamp"] > cutoff]
            return len(recent) < quota_per_minute

    def get_quota_remaining(self, user_id: str, quota_per_minute: int) -> int:
        """Return number of requests remaining in current minute window."""
        cutoff = time.time() - 60
        with self._lock:
            u = self._users.get(user_id)
            if u is None:
                return quota_per_minute
            recent = [j for j in u["recent_jobs"] if j["timestamp"] > cutoff]
            return max(0, quota_per_minute - len(recent))


# Global tracker instance
usage_tracker = UsageTracker()

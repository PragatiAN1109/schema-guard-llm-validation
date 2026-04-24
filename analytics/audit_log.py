"""
SchemaGuard — Audit Log

Structured audit logging for compliance and debugging.
Every API request produces an audit entry with user, payload summary, and result.

In production, replace with:
    - Elasticsearch for searchable audit logs
    - AWS CloudWatch / CloudTrail
    - PostgreSQL with partitioned tables
"""

import time
import json
import threading
from pathlib import Path
from typing import Optional


AUDIT_DIR = Path(__file__).parent.parent / "audit_logs"


class AuditLog:
    """Append-only audit logger."""

    def __init__(self):
        self._lock = threading.Lock()
        self._entries: list[dict] = []
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    def log(self, user_id: str, action: str, domain: str = None,
            job_id: str = None, payload_summary: dict = None,
            result_summary: dict = None, status_code: int = 200):
        """Write an audit entry."""
        entry = {
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "user_id": user_id,
            "action": action,
            "domain": domain,
            "job_id": job_id,
            "payload_summary": payload_summary or {},
            "result_summary": result_summary or {},
            "status_code": status_code,
        }

        with self._lock:
            self._entries.append(entry)

        # Write to file (non-blocking best-effort)
        try:
            with open(AUDIT_DIR / "api_audit.jsonl", "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

        return entry

    def get_user_entries(self, user_id: str, limit: int = 50) -> list[dict]:
        """Return recent audit entries for a user."""
        with self._lock:
            user_entries = [e for e in self._entries if e["user_id"] == user_id]
        user_entries.sort(key=lambda e: e["timestamp"], reverse=True)
        return user_entries[:limit]

    def get_recent(self, limit: int = 100) -> list[dict]:
        """Return most recent audit entries across all users."""
        with self._lock:
            entries = list(self._entries)
        entries.sort(key=lambda e: e["timestamp"], reverse=True)
        return entries[:limit]

    def count_by_user(self) -> dict:
        """Return request counts per user."""
        with self._lock:
            counts = {}
            for e in self._entries:
                uid = e["user_id"]
                counts[uid] = counts.get(uid, 0) + 1
            return counts


# Global audit log
audit_log = AuditLog()

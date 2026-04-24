"""
SchemaGuard — In-Memory Result Store (Multi-User)

Thread-safe storage for validation job results with user ownership.

In production, replace with:
    - Redis for job status (TTL-based expiry)
    - PostgreSQL/DynamoDB for persistent result storage
"""

import threading
import time
from typing import Optional
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResultStore:
    """Thread-safe in-memory store for validation jobs and results."""

    def __init__(self, max_size: int = 10000):
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._max_size = max_size

    def create_job(self, job_id: str, domain: str, record_count: int = 1,
                   user_id: str = None) -> dict:
        """Register a new job as pending."""
        job = {
            "job_id": job_id,
            "user_id": user_id,
            "domain": domain,
            "record_count": record_count,
            "status": JobStatus.PENDING,
            "created_at": time.time(),
            "updated_at": time.time(),
            "result": None,
            "error": None,
            "retries": 0,
        }
        with self._lock:
            if len(self._jobs) >= self._max_size:
                self._evict_oldest()
            self._jobs[job_id] = job
        return job

    def update_status(self, job_id: str, status: JobStatus, result: dict = None, error: str = None):
        """Update job status and optionally attach result or error."""
        with self._lock:
            if job_id not in self._jobs:
                return
            self._jobs[job_id]["status"] = status
            self._jobs[job_id]["updated_at"] = time.time()
            if result is not None:
                self._jobs[job_id]["result"] = result
            if error is not None:
                self._jobs[job_id]["error"] = error

    def increment_retry(self, job_id: str) -> int:
        """Increment retry count and return new count."""
        with self._lock:
            if job_id not in self._jobs:
                return -1
            self._jobs[job_id]["retries"] += 1
            return self._jobs[job_id]["retries"]

    def get_job(self, job_id: str, user_id: str = None) -> Optional[dict]:
        """Retrieve a job by ID. If user_id given, enforce ownership."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if user_id and job.get("user_id") and job["user_id"] != user_id:
                return None  # user doesn't own this job
            return {**job}

    def get_result(self, job_id: str, user_id: str = None) -> Optional[dict]:
        """Retrieve just the result for a completed job."""
        job = self.get_job(job_id, user_id=user_id)
        if job is None:
            return None
        if job["status"] == JobStatus.COMPLETED:
            return job["result"]
        return None

    def list_jobs(self, status: JobStatus = None, user_id: str = None, limit: int = 50) -> list[dict]:
        """List jobs, optionally filtered by status and/or user."""
        with self._lock:
            jobs = list(self._jobs.values())
        if user_id:
            jobs = [j for j in jobs if j.get("user_id") == user_id]
        if status:
            jobs = [j for j in jobs if j["status"] == status]
        jobs.sort(key=lambda j: j["created_at"], reverse=True)
        return [self._summary(j) for j in jobs[:limit]]

    def get_stats(self) -> dict:
        """Return aggregate job statistics."""
        with self._lock:
            jobs = list(self._jobs.values())
        total = len(jobs)
        by_status = {}
        for j in jobs:
            s = j["status"]
            by_status[s] = by_status.get(s, 0) + 1

        completed = [j for j in jobs if j["status"] == JobStatus.COMPLETED and j.get("result")]
        avg_time = 0.0
        if completed:
            times = [j["result"].get("audit_entry", {}).get("processing_time_ms", 0)
                     for j in completed if isinstance(j.get("result"), dict)]
            avg_time = sum(times) / len(times) if times else 0.0

        return {
            "total_jobs": total,
            "by_status": by_status,
            "avg_processing_time_ms": round(avg_time, 2),
        }

    def _summary(self, job: dict) -> dict:
        return {
            "job_id": job["job_id"],
            "user_id": job.get("user_id"),
            "domain": job["domain"],
            "status": job["status"],
            "record_count": job["record_count"],
            "created_at": job["created_at"],
            "retries": job["retries"],
        }

    def _evict_oldest(self):
        if not self._jobs:
            return
        sorted_ids = sorted(self._jobs.keys(), key=lambda k: self._jobs[k]["created_at"])
        evict_count = max(1, len(sorted_ids) // 10)
        for jid in sorted_ids[:evict_count]:
            del self._jobs[jid]


# Global store instance
store = ResultStore()

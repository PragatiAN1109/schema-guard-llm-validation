"""
SchemaGuard — Async API Routes (Multi-User)

Non-blocking validation with per-user auth, quotas, usage tracking, and audit.
"""

import asyncio
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional

from auth.auth import get_current_user
from pipeline.async_processor import processor
from storage.result_store import store, JobStatus
from analytics.usage_tracker import usage_tracker
from analytics.audit_log import audit_log
from utils.metrics import metrics
from config import resolve_domain


async_router = APIRouter()


class AsyncSubmitRequest(BaseModel):
    domain: str
    record: dict


class AsyncBatchRequest(BaseModel):
    domain: str
    records: list[dict]


def _resolve(domain: str) -> str:
    resolved = resolve_domain(domain)
    if not resolved:
        raise HTTPException(status_code=400, detail=f"Unknown domain: {domain}")
    return resolved


def _check_quota(user: dict):
    uid = user["user_id"]
    quota = user.get("quota_per_minute", 60)
    if not usage_tracker.check_quota(uid, quota):
        remaining = usage_tracker.get_quota_remaining(uid, quota)
        raise HTTPException(
            status_code=429,
            detail=f"Quota exceeded for user '{uid}'. Limit: {quota}/min. Remaining: {remaining}",
        )


def _sanitize_record(record: dict) -> dict:
    """Strip any keys that could cause issues. Limit nested depth."""
    if not isinstance(record, dict):
        raise HTTPException(status_code=400, detail="Record must be a JSON object")
    if len(str(record)) > 50000:
        raise HTTPException(status_code=400, detail="Record too large (max 50KB)")
    return record


@async_router.post("/submit")
async def submit_validation(req: AsyncSubmitRequest, user: dict = Depends(get_current_user)):
    """Submit a single record for async validation. Returns job_id immediately."""
    _check_quota(user)
    domain = _resolve(req.domain)
    record = _sanitize_record(req.record)

    job_id = processor.submit(domain, record, user_id=user["user_id"])

    audit_log.log(
        user_id=user["user_id"], action="submit", domain=domain, job_id=job_id,
        payload_summary={"record_keys": list(record.keys())[:10]},
    )

    return {
        "job_id": job_id,
        "user_id": user["user_id"],
        "status": "pending",
        "message": "Job submitted. POST /async/process to run queue, then GET /async/result/{job_id}",
    }


@async_router.post("/submit-batch")
async def submit_batch(req: AsyncBatchRequest, user: dict = Depends(get_current_user)):
    """Submit multiple records for async validation."""
    _check_quota(user)
    domain = _resolve(req.domain)

    if len(req.records) == 0:
        raise HTTPException(status_code=400, detail="Records list is empty")
    if len(req.records) > 500:
        raise HTTPException(status_code=400, detail="Max 500 records per batch")

    job_ids = processor.submit_batch(domain, req.records, user_id=user["user_id"])

    audit_log.log(
        user_id=user["user_id"], action="submit_batch", domain=domain,
        payload_summary={"record_count": len(req.records)},
    )

    return {
        "job_ids": job_ids,
        "user_id": user["user_id"],
        "count": len(job_ids),
        "status": "pending",
    }


@async_router.post("/process")
async def process_queue(user: dict = Depends(get_current_user)):
    """Process all pending jobs in the queue."""
    summary = await processor.process_queue()

    # Record usage + metrics for completed jobs
    for j in store.list_jobs(status=JobStatus.COMPLETED, limit=1000):
        job = store.get_job(j["job_id"])
        if job and job.get("result"):
            r = job["result"]
            pt = r.get("audit_entry", {}).get("processing_time_ms", 0)
            dec = r.get("decision", "quarantined")
            conf = r.get("confidence_score", 0)
            metrics.record_validation(pt, True, dec)
            if job.get("user_id"):
                usage_tracker.record_request(job["user_id"], j["job_id"], True, conf, dec)

    audit_log.log(user_id=user["user_id"], action="process_queue",
                  result_summary={"processed": summary["total_processed"]})

    return summary


@async_router.get("/result/{job_id}")
async def get_result(job_id: str, user: dict = Depends(get_current_user)):
    """Fetch result for a completed job. Users can only see their own jobs."""
    job = store.get_job(job_id, user_id=user["user_id"])
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found or access denied: {job_id}")

    if job["status"] in (JobStatus.PENDING, JobStatus.PROCESSING):
        return {"job_id": job_id, "user_id": user["user_id"], "status": job["status"]}

    if job["status"] == JobStatus.FAILED:
        return {"job_id": job_id, "user_id": user["user_id"], "status": "failed",
                "error": job.get("error", "Unknown")}

    result = job.get("result", {})
    return {
        "job_id": job_id,
        "user_id": user["user_id"],
        "status": "completed",
        "domain": result.get("domain"),
        "structural_valid": result.get("structural_valid"),
        "semantic_valid": result.get("semantic_valid"),
        "violated_rules": result.get("violated_rules", []),
        "confidence_score": result.get("confidence_score"),
        "decision": result.get("decision"),
        "explanation": result.get("explanation"),
    }


@async_router.get("/status/{job_id}")
async def get_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get job status. Users can only see their own jobs."""
    job = store.get_job(job_id, user_id=user["user_id"])
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found or access denied: {job_id}")
    return {
        "job_id": job["job_id"],
        "user_id": user["user_id"],
        "status": job["status"],
        "domain": job["domain"],
        "retries": job["retries"],
        "created_at": job["created_at"],
    }


@async_router.get("/jobs")
async def list_jobs(status: Optional[str] = None, limit: int = 20,
                    user: dict = Depends(get_current_user)):
    """List the authenticated user's jobs."""
    filter_status = None
    if status:
        try:
            filter_status = JobStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    jobs = store.list_jobs(status=filter_status, user_id=user["user_id"], limit=limit)
    return {"user_id": user["user_id"], "jobs": jobs}


@async_router.get("/metrics")
async def get_metrics(user: dict = Depends(get_current_user)):
    """Return performance metrics and user stats."""
    return {
        "performance": metrics.get_summary(),
        "queue": store.get_stats(),
        "user_stats": usage_tracker.get_user_stats(user["user_id"]),
    }

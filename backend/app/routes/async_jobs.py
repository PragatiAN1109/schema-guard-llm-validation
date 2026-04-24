"""
Async job routes — submit, process, fetch results.
Delegates to the existing pipeline/async_processor.py engine.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

from pipeline.async_processor import processor
from storage.result_store import store, JobStatus

router = APIRouter()


class AsyncSubmitRequest(BaseModel):
    domain: str
    record: dict


class AsyncBatchRequest(BaseModel):
    domain: str
    records: list[dict]


@router.post("/submit")
async def submit(req: AsyncSubmitRequest):
    job_id = processor.submit(req.domain, req.record)
    return {"job_id": job_id, "status": "pending"}


@router.post("/submit-batch")
async def submit_batch(req: AsyncBatchRequest):
    if not req.records:
        raise HTTPException(status_code=400, detail="Empty records list")
    job_ids = processor.submit_batch(req.domain, req.records)
    return {"job_ids": job_ids, "count": len(job_ids), "status": "pending"}


@router.post("/process")
async def process_queue():
    summary = await processor.process_queue()
    return summary


@router.get("/result/{job_id}")
async def get_result(job_id: str):
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    if job["status"] in (JobStatus.PENDING, JobStatus.PROCESSING):
        return {"job_id": job_id, "status": job["status"]}
    if job["status"] == JobStatus.FAILED:
        return {"job_id": job_id, "status": "failed", "error": job.get("error")}
    result = job.get("result", {})
    return {
        "job_id": job_id, "status": "completed",
        "domain": result.get("domain"),
        "structural_valid": result.get("structural_valid"),
        "semantic_valid": result.get("semantic_valid"),
        "violated_rules": result.get("violated_rules", []),
        "confidence_score": result.get("confidence_score"),
        "decision": result.get("decision"),
        "explanation": result.get("explanation"),
    }


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return {"job_id": job["job_id"], "status": job["status"], "domain": job["domain"], "retries": job["retries"]}


@router.get("/jobs")
async def list_jobs(status: Optional[str] = None, limit: int = 20):
    filter_status = JobStatus(status) if status else None
    return {"jobs": store.list_jobs(status=filter_status, limit=limit)}

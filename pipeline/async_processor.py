"""
SchemaGuard — Async Validation Processor (Multi-User)

Processes validation jobs concurrently with user ownership tracking.
"""

import asyncio
import uuid
import time
from typing import Optional
from validator.pipeline import validate_record
from storage.result_store import store, JobStatus
from pipeline.queue import ValidationQueue, ValidationJob, queue
from utils.logger import get_logger

logger = get_logger("pipeline.async")

MAX_CONCURRENCY = 10


class AsyncProcessor:
    """Async validation processor with user tracking."""

    def __init__(self, validation_queue: ValidationQueue = None, concurrency: int = MAX_CONCURRENCY):
        self._queue = validation_queue or queue
        self._concurrency = concurrency
        self._semaphore: Optional[asyncio.Semaphore] = None

    def submit(self, domain: str, record: dict, user_id: str = None) -> str:
        """Submit a single record for async validation. Returns job_id."""
        prefix = "HC" if "healthcare" in str(domain) else "FN"
        job_id = f"{prefix}-async-{uuid.uuid4().hex[:8]}"
        store.create_job(job_id, domain, record_count=1, user_id=user_id)
        self._queue.enqueue(domain, record, job_id=job_id)
        return job_id

    def submit_batch(self, domain: str, records: list[dict], user_id: str = None) -> list[str]:
        """Submit multiple records. Returns job_ids."""
        job_ids = []
        batch_prefix = uuid.uuid4().hex[:6]
        for i, record in enumerate(records):
            prefix = "HC" if "healthcare" in str(domain) else "FN"
            job_id = f"{prefix}-async-{batch_prefix}-{i:03d}"
            store.create_job(job_id, domain, record_count=1, user_id=user_id)
            self._queue.enqueue(domain, record, job_id=job_id)
            job_ids.append(job_id)
        logger.info(f"Submitted batch of {len(records)} jobs for user={user_id}")
        return job_ids

    async def process_queue(self) -> dict:
        """Process all jobs in queue with concurrency control."""
        self._semaphore = asyncio.Semaphore(self._concurrency)
        start = time.perf_counter()
        outcomes = await self._queue.process_all(self._handle_job)
        elapsed = (time.perf_counter() - start) * 1000
        succeeded = sum(1 for o in outcomes if o["success"])
        failed = sum(1 for o in outcomes if not o["success"])
        return {
            "total_processed": len(outcomes),
            "succeeded": succeeded,
            "failed": failed,
            "processing_time_ms": round(elapsed, 2),
            "queue_stats": self._queue.get_stats(),
            "store_stats": store.get_stats(),
        }

    async def _handle_job(self, job: ValidationJob) -> dict:
        async with self._semaphore:
            store.update_status(job.job_id, JobStatus.PROCESSING)
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, validate_record, job.record, job.domain, job.job_id
                )
                store.update_status(job.job_id, JobStatus.COMPLETED, result=result)
                return result
            except Exception as e:
                retries = store.increment_retry(job.job_id)
                if retries > 2:
                    store.update_status(job.job_id, JobStatus.FAILED, error=str(e))
                else:
                    store.update_status(job.job_id, JobStatus.PENDING)
                raise

    def get_result(self, job_id: str, user_id: str = None) -> Optional[dict]:
        return store.get_result(job_id, user_id=user_id)

    def get_job_status(self, job_id: str, user_id: str = None) -> Optional[dict]:
        return store.get_job(job_id, user_id=user_id)


processor = AsyncProcessor()

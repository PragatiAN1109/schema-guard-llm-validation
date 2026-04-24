"""
SchemaGuard — Validation Queue

Simulates message-queue-based job processing (Kafka/SQS pattern).
Jobs are enqueued, processed sequentially or in batches, with retry on failure.

In production, replace with:
    - AWS SQS / Kafka for distributed queue
    - Celery for async task execution
    - Dead-letter queue for permanently failed jobs
"""

import asyncio
import uuid
import time
from collections import deque
from typing import Callable, Any
from utils.logger import get_logger

logger = get_logger("pipeline.queue")

MAX_RETRIES = 2


class ValidationJob:
    """A single validation job in the queue."""

    def __init__(self, job_id: str, domain: str, record: dict, job_type: str = "single"):
        self.job_id = job_id
        self.domain = domain
        self.record = record
        self.job_type = job_type  # "single" or "batch"
        self.retries = 0
        self.created_at = time.time()

    def __repr__(self):
        return f"<Job {self.job_id} [{self.job_type}] retries={self.retries}>"


class ValidationQueue:
    """
    In-memory FIFO queue for validation jobs.

    Supports:
        - Enqueue single or batch jobs
        - Sequential processing with callback
        - Retry on failure (up to MAX_RETRIES)
        - Dead-letter collection for permanently failed jobs
    """

    def __init__(self):
        self._queue: deque[ValidationJob] = deque()
        self._dead_letter: list[ValidationJob] = []
        self._processed = 0
        self._failed = 0

    def enqueue(self, domain: str, record: dict, job_id: str = None, job_type: str = "single") -> str:
        """Add a job to the queue. Returns job_id."""
        if job_id is None:
            prefix = "HC" if "healthcare" in domain else "FN"
            job_id = f"{prefix}-job-{uuid.uuid4().hex[:8]}"
        job = ValidationJob(job_id=job_id, domain=domain, record=record, job_type=job_type)
        self._queue.append(job)
        logger.info(f"Enqueued {job}")
        return job_id

    def enqueue_batch(self, domain: str, records: list[dict]) -> list[str]:
        """Enqueue multiple records as individual jobs. Returns list of job_ids."""
        job_ids = []
        batch_prefix = uuid.uuid4().hex[:6]
        for i, record in enumerate(records):
            prefix = "HC" if "healthcare" in domain else "FN"
            job_id = f"{prefix}-batch-{batch_prefix}-{i:03d}"
            self.enqueue(domain, record, job_id=job_id, job_type="batch")
            job_ids.append(job_id)
        return job_ids

    def size(self) -> int:
        return len(self._queue)

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    async def process_all(self, handler: Callable[[ValidationJob], Any]) -> list[dict]:
        """
        Process all jobs in queue using the provided handler.
        Retries failed jobs up to MAX_RETRIES times.
        Returns list of (job_id, success, result_or_error) dicts.
        """
        outcomes = []

        while self._queue:
            job = self._queue.popleft()

            try:
                result = await self._execute(handler, job)
                outcomes.append({"job_id": job.job_id, "success": True, "result": result})
                self._processed += 1
                logger.info(f"Completed {job}")
            except Exception as e:
                job.retries += 1
                if job.retries <= MAX_RETRIES:
                    logger.warning(f"Retry {job.retries}/{MAX_RETRIES} for {job}: {e}")
                    self._queue.append(job)  # re-enqueue
                else:
                    logger.error(f"Failed permanently: {job}: {e}")
                    self._dead_letter.append(job)
                    self._failed += 1
                    outcomes.append({"job_id": job.job_id, "success": False, "error": str(e)})

        return outcomes

    async def _execute(self, handler: Callable, job: ValidationJob) -> Any:
        """Execute a handler, supporting both sync and async handlers."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(job)
        else:
            return handler(job)

    def get_dead_letter(self) -> list[dict]:
        """Return permanently failed jobs."""
        return [{"job_id": j.job_id, "domain": j.domain, "retries": j.retries} for j in self._dead_letter]

    def get_stats(self) -> dict:
        return {
            "queued": len(self._queue),
            "processed": self._processed,
            "failed": self._failed,
            "dead_letter": len(self._dead_letter),
        }


# Global queue instance
queue = ValidationQueue()

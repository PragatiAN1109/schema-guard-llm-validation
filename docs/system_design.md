# System Design — SchemaGuard at Scale

## Current Architecture

```
Client → FastAPI → Validation Pipeline → Result
                       │
                       ├── Structural (jsonschema)
                       ├── Semantic (rule engine)
                       ├── Confidence (scorer)
                       ├── Decision (router)
                       └── Audit (JSONL)
```

Single process, synchronous by default. Async pipeline available via `/async/*` endpoints with in-memory queue and result store.

## How This Scales

### Level 1: Current (Demo / Dev)
- Single FastAPI process
- In-memory queue + result store
- File-based audit logs
- Good for: demos, development, small batch validation (< 1000 records)

### Level 2: Production Single-Node
Replace in-memory components:
- **Queue** → Redis List or AWS SQS
- **Result Store** → Redis (with TTL for job status) + PostgreSQL (for persistent results)
- **Audit** → Write to PostgreSQL or ship to Elasticsearch
- **Rate Limiting** → Redis sliding window
- Run with `gunicorn` + `uvicorn` workers (multi-process)

### Level 3: Distributed
- **Queue** → Kafka topics (one per domain)
- **Workers** → Celery workers or Kubernetes pods consuming from Kafka
- **Autoscaling** → Scale workers based on queue depth
- **Storage** → DynamoDB or PostgreSQL with read replicas
- **Monitoring** → Prometheus + Grafana for latency, throughput, error rate
- **Drift** → Run as a scheduled batch job, not per-request

## Where Real Systems Would Use External Services

| Component | Current | Production Replacement |
|-----------|---------|----------------------|
| Job Queue | `pipeline/queue.py` (in-memory deque) | Kafka / SQS / Redis Streams |
| Result Store | `storage/result_store.py` (in-memory dict) | Redis + PostgreSQL |
| Async Workers | `asyncio` in-process | Celery workers / K8s pods |
| Rate Limiting | `utils/rate_limiter.py` (in-memory) | Redis sliding window / API Gateway |
| Metrics | `utils/metrics.py` (in-memory) | Prometheus client_python |
| Audit Logs | JSONL files | Elasticsearch / CloudWatch |
| Drift Baseline | JSON files | S3 / database |

## Tradeoffs Made

**In-memory vs. persistent storage:**
Chose in-memory for zero-dependency setup. The interfaces are clean — replacing `ResultStore` with a Redis-backed implementation requires changing one import.

**asyncio vs. Celery:**
asyncio is simpler for a single-process demo. Celery adds broker dependencies (Redis/RabbitMQ). The async processor wraps sync validation in `run_in_executor` to avoid blocking the event loop.

**Queue simulation vs. real broker:**
The `ValidationQueue` implements enqueue/dequeue/retry/dead-letter — the same contract that SQS or Kafka would provide. Production migration means implementing the same interface against a real broker.

**Rate limiting scope:**
Global rate limit (120/min) vs. per-client. Per-client requires authentication, which is out of scope. The `RateLimiter` class accepts a `client_id` parameter — adding auth just means passing the user ID.

## Bottlenecks

1. **Schema loading:** Schemas are cached after first load. No bottleneck at scale.

2. **Rule execution:** Rules are pure Python functions. Each runs in microseconds. 10 rules × N records is O(N) and fast. Not a bottleneck until N > 100K.

3. **Audit logging:** File-based JSONL is a bottleneck under concurrent writes. Production fix: write to a buffer, flush in batches, or ship to a log aggregator.

4. **Drift detection:** Requires iterating all records in a batch. O(N × fields). For batches > 10K, run as a background job, not inline.

5. **Result store eviction:** In-memory store evicts oldest 10% when full. Production fix: Redis with TTL-based expiry.

## Request Flow (Async)

```
1. Client POSTs to /async/submit
   → job_id created, stored as PENDING
   → record enqueued in ValidationQueue
   → 202 response with job_id (non-blocking)

2. Client (or scheduler) POSTs to /async/process
   → queue drains all pending jobs
   → each job: PENDING → PROCESSING → COMPLETED (or FAILED after retries)
   → results stored in ResultStore

3. Client GETs /async/result/{job_id}
   → if COMPLETED: return full validation result
   → if PENDING/PROCESSING: return status
   → if FAILED: return error

4. Client GETs /async/metrics
   → throughput, latency, success rate, queue depth
```

## What I'd Build Next

1. **WebSocket endpoint** for real-time result streaming during batch processing
2. **Scheduled drift detection** — cron job that runs nightly against the day's records
3. **Alert webhook** — POST to Slack/PagerDuty when drift exceeds threshold
4. **Result pagination** — `/async/jobs?page=2&per_page=50` for large job lists
5. **Job cancellation** — `DELETE /async/job/{job_id}` to remove pending jobs from queue

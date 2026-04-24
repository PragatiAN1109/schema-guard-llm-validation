# System Tradeoffs — SchemaGuard

## Consistency vs. Availability

**Choice: Favor consistency.**

Every validation produces the same result for the same input — deterministic rules, deterministic scoring. We never return a cached stale result or approximate a score.

**Tradeoff:** If the validation pipeline is overloaded, requests queue rather than degrade. In production with Kafka, this means consumer lag increases but data quality is never compromised. For a compliance-critical system (healthcare, finance), consistency is non-negotiable.

**Where we'd relax this:** Drift detection. Drift is a statistical signal computed over batches — it's inherently approximate. Running drift on a sample rather than the full batch is an acceptable availability optimization.

## Synchronous vs. Asynchronous Validation

**Choice: Support both.**

Sync (`/validate`) is simpler and fine for single records. Async (`/async/submit` → `/async/process` → `/async/result`) is necessary for batch processing and high-throughput pipelines.

**Tradeoff:** Async adds complexity — job tracking, queue management, status polling, failure retries. But without it, a 1000-record batch blocks the API thread for seconds.

**The right pattern in production:** Sync for real-time single-record validation (API gateway use case). Async for batch ingestion (ETL pipeline use case). Let the client choose.

## Rule-Based vs. ML-Based Validation

**Choice: Deterministic rules.**

Every rule is a Python function that checks a specific cross-field relationship. Same input → same output. Full audit trail. No training data required.

**Tradeoff:** Rules only catch patterns you've explicitly coded. An LLM classifier could catch novel patterns — a suspicious combination of fields that no rule anticipated. But LLM classifiers are non-deterministic, non-auditable, and expensive per call.

**Where ML fits:** As a *complement*, not a replacement. Run rules first (fast, deterministic, auditable). Then optionally run an ML scorer as a second signal. The confidence scoring framework already supports adding ML-derived penalties.

## Batch vs. Real-Time Processing

**Choice: Batch-first with real-time support.**

Single-record sync validation processes in < 2ms. Batch validation processes N records sequentially with drift detection at the end. The async pipeline adds concurrency.

**Tradeoff:** Real-time streaming (validate every record as it's produced) requires persistent connections, back-pressure handling, and consumer group management. Our queue abstraction simulates this but isn't a real stream processor.

**In production:** Use Kafka topics per domain. Consumer groups process records in parallel. Drift detection runs as a scheduled batch job against the day's records, not inline.

## In-Memory vs. Persistent Storage

**Choice: In-memory for zero-dependency setup.**

The result store, queue, rate limiter, and metrics are all in-memory. This makes the system runnable with `pip install` and nothing else.

**Tradeoff:** Data is lost on restart. No horizontal scaling (each process has its own store). No durability guarantees.

**Production replacements are documented inline:**
- Result store → Redis (TTL for status) + PostgreSQL (persistent results)
- Queue → Kafka / SQS
- Rate limiter → Redis sliding window
- Metrics → Prometheus
- Audit log → Elasticsearch

The interfaces are clean — swapping implementations requires changing one import, not rewriting the pipeline.

## Retry vs. Fail-Fast

**Choice: Retry twice, then dead-letter.**

Failed jobs get 2 retries before being moved to the dead-letter collection. This handles transient errors (timeout, resource contention) without infinite loops.

**Tradeoff:** Retries add latency for jobs that will ultimately fail. Three attempts at a job that crashes on a malformed record wastes ~6ms. But that's negligible compared to the cost of dropping a valid job due to a transient glitch.

**Circuit breaker addition:** If a module fails repeatedly (e.g., drift detector can't load baseline), the circuit breaker opens and routes to a safe fallback. This prevents one broken module from cascading into queue buildup.

## Per-User Isolation vs. Global Processing

**Choice: User-scoped jobs with global queue.**

Jobs are tagged with user_id and isolated at the storage layer — users can only see their own results. But the processing queue is global — all jobs are processed by the same worker pool.

**Tradeoff:** A noisy user submitting thousands of jobs can delay other users' jobs. In production, you'd add per-user queue partitioning or priority queues.

**Where this is fine:** For a multi-tenant SaaS with quota enforcement, the per-user rate limit prevents any single user from monopolizing the queue. The quota system (X requests/minute per user) is the first line of defense.

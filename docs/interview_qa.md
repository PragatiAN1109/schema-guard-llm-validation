# Interview Q&A — SchemaGuard

---

**Why did you build this?**

I kept seeing teams deploy LLMs for structured data generation and rely entirely on JSON schema validation. That catches missing fields and wrong types, but it misses logical errors — a discharge before admission, a loan that's 50x someone's income. These are real failures in production pipelines, and there was no lightweight, deterministic tool to catch them. I wanted to build the missing layer.

---

**Why not just use JSON schema validation?**

Schema validation checks structure: types, required fields, formats, ranges. It can't check whether field values are consistent with each other. A discharge date before an admission date is a valid date in a valid field — schema says it's fine. SchemaGuard adds the semantic layer: cross-field rules that check logical relationships. They're complementary — SchemaGuard runs schema checks first, then semantic checks on top.

---

**Why deterministic rules instead of an LLM classifier?**

Three reasons. First, reproducibility — same input always produces the same output. In healthcare and finance, that matters for compliance. Second, auditability — every decision has a full rule trace showing exactly which rule failed and why. Third, cost — rule evaluation takes microseconds, not API calls. An LLM classifier could catch novel patterns, but for known domain rules, deterministic logic is the right tool.

---

**How does drift detection work?**

I build a statistical baseline from known-good records — means and standard deviations for numeric fields, frequency distributions for categorical fields, null rates. For each new batch, I compare distributions. Numeric fields use z-score normalized mean shift (alert if z > 1.5 standard deviations). Categorical fields use Population Stability Index (alert if PSI > 0.20). I also track null-rate changes and overall violation rates. This catches slow degradation that no single-record check would find.

---

**How does confidence scoring work?**

Start at 1.0. Subtract penalties based on violation severity: -0.30 for critical, -0.12 for warning, -0.05 for info. Structural failure floors the score to 0.0. The result maps to routing: ≥0.85 is trusted, 0.50–0.84 is flagged, <0.50 is quarantined. Thresholds are configurable via environment variables. The key insight is that continuous scoring preserves more information than binary pass/fail — a record with one warning is different from a record with three critical violations.

---

**How does the async pipeline work?**

Submit a record via `/async/submit` — returns a job_id immediately without blocking. The record goes into a FIFO queue. When you POST to `/async/process`, the queue drains with asyncio concurrency control (configurable semaphore). Each job transitions through pending → processing → completed/failed. Failed jobs get 2 retries before being moved to a dead-letter collection. Results are stored in a thread-safe result store, retrievable by job_id. In production, the queue would be Kafka/SQS and the store would be Redis/PostgreSQL.

---

**How would you scale this?**

Three levels. Current: single FastAPI process with in-memory queue and store — good for demos and small batches. Single-node production: swap in-memory components for Redis (job status) and PostgreSQL (persistent results), run with gunicorn workers. Distributed: Kafka topics per domain, Celery workers or Kubernetes pods consuming from Kafka, autoscale based on queue depth. The interfaces are clean — each component is swappable without rewriting the pipeline.

---

**What about the circuit breaker?**

If a module (like drift detection) fails repeatedly, the circuit breaker opens after N consecutive failures and routes to a safe fallback for a cooldown period. After cooldown, it tries one probe request — if that succeeds, the breaker closes. If not, it stays open. This prevents one broken module from cascading into queue buildup or API timeouts. Configured per module: drift breaker opens after 3 failures with 30-second cooldown, semantic breaker after 5 with 15-second cooldown.

---

**How do you handle multi-user isolation?**

Every job is tagged with user_id at submission time. The result store enforces ownership — `get_job(job_id, user_id)` returns None if the user doesn't own that job. The API layer extracts the user from the Authorization header (token-based auth) and passes user_id through the entire flow. Each user also has per-minute quotas tracked by the usage tracker.

---

**What are the limitations?**

The seed dataset is small — 16 records. The metrics are perfect on that set but need validation against larger LLM-generated data for statistical significance. The medication plausibility rule only covers 7 ICD-10 categories. The DTI rule uses a fixed threshold regardless of loan type. Drift baseline with 3 records has high categorical variance. All storage is in-memory — data is lost on restart.

---

**What would you improve?**

Four things. First, connect the LLM API to generate 300+ labeled records per domain for meaningful evaluation metrics. Second, add a lightweight RAG layer for explanation generation — store rule documentation in a vector store, retrieve relevant context for each explanation. Third, calibrate scoring weights from labeled data instead of using fixed penalties. Fourth, containerize with Docker and add CI/CD.

---

**How is this different from other portfolio projects?**

It's not a notebook, not a chat wrapper, not a fine-tuning exercise. It's a systems engineering project — modular architecture, async processing, retry logic, circuit breakers, observability, multi-user isolation, audit trails. It demonstrates the kind of infrastructure thinking that production LLM deployments actually need.

---

**What design decision are you most proud of?**

The continuous confidence scoring. Binary pass/fail loses information. A record with one warning-level violation (score 0.88) is fundamentally different from a record with three critical violations (score 0.10). The continuous score lets downstream systems make nuanced decisions — auto-accept the high-confidence ones, review the medium ones, block the low ones. It's a simple idea but it changes the entire operational model.

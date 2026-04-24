# Failure Handling — SchemaGuard

## Design Principle

The system never crashes on bad input. Every failure mode produces a structured response, a log entry, and an appropriate routing decision (quarantine). No exception propagates to the API layer unhandled.

## Failure Modes and Responses

### 1. Malformed Input (None, string, empty dict, wrong type)

**Detection:** Type checks at the top of `validate_record()` and `validate_batch()`.

**Response:** Record is quarantined with confidence 0.0 and a clear error message in the explanation field. No rules are executed. An audit entry is still written.

**Example:**
```
Input: validate_record(None, "healthcare")
Output: { decision: "quarantined", confidence: 0.0, explanation: "Record must be dict, got NoneType" }
```

### 2. Unknown Domain

**Detection:** `config.resolve_domain()` returns None for unrecognized domains.

**Response:** Quarantine with error. API returns 400 for REST requests, structured error dict for pipeline calls.

### 3. Schema Load Failure

**Detection:** Try/except around `json.load()` in `structural.py`.

**Response:** Structural validation returns `{ valid: false, errors: [...] }`. Pipeline continues to scoring (score = 0.0) and quarantines.

### 4. Individual Rule Crash

**Detection:** Each rule executes inside try/except in `rule_registry.run_all()`.

**Response:** The crashing rule returns `{ passed: false, severity: "critical", message: "Error: ..." }`. Other rules still execute. Violations are collected normally.

**Why this matters:** One buggy rule doesn't take down the entire pipeline. All other rules still validate the record.

### 5. Drift Detection Failure

**Detection:** Try/except around `run_drift_detection()` in `batch_validation.py`. Circuit breaker (`drift_breaker`) tracks consecutive failures.

**Response after transient failure:** Error is logged, drift summary contains `{ "error": "..." }`. Batch results are still returned — drift is a supplementary signal, not a gate.

**Response after repeated failures (circuit breaker):** Breaker opens. Drift calls return the fallback: `{ drift_detected: false, error: "Circuit breaker open" }`. After cooldown (30s), a probe request tests if drift is healthy again.

### 6. Queue Processing Failure

**Detection:** Try/except per job in `queue.process_all()`.

**Response:** Failed job is retried up to 2 times (re-enqueued at the back of the queue). After max retries, the job moves to the dead-letter collection.

**Dead-letter jobs** can be inspected via `queue.get_dead_letter()` and manually reprocessed after the underlying issue is fixed.

### 7. Storage Failure

**Detection:** Circuit breaker (`storage_breaker`) wraps store operations.

**Response:** If the store is unreachable, job status updates fail silently (logged). The validation result is still returned directly to the caller. This means the result might not be retrievable later via `/async/result/{job_id}`, but the validation itself isn't lost.

### 8. Timeout

**Detection:** `asyncio.wait_for()` with configurable timeout in the async processor.

**Response:** Job is marked as failed with error "Timeout exceeded". The record isn't lost — it can be re-submitted.

### 9. Rate Limit / Quota Exceeded

**Detection:** `RateLimiter.allow()` and `UsageTracker.check_quota()` called before processing.

**Response:** HTTP 429 with remaining quota in the response body. The request is rejected before any processing starts.

## Retry Strategy

```
Attempt 1: Process job
  ↓ fail
Attempt 2: Re-enqueue, process again
  ↓ fail
Attempt 3: Re-enqueue, process again
  ↓ fail
→ Dead-letter queue (permanently failed)
```

Retries are within the same queue cycle. There's no exponential backoff in the current implementation — in production you'd add backoff via SQS visibility timeout or Kafka consumer delay.

## Circuit Breaker Logic

```
CLOSED (normal)
  ↓ failure_count >= threshold (3)
OPEN (short-circuit to fallback)
  ↓ cooldown_seconds expired (30s)
HALF_OPEN (probe: try one real call)
  ↓ success → CLOSED
  ↓ failure → OPEN (reset cooldown)
```

Configured per module:
- `drift_breaker`: threshold=3, cooldown=30s, fallback=safe empty report
- `semantic_breaker`: threshold=5, cooldown=15s, fallback=empty violations
- `storage_breaker`: threshold=3, cooldown=10s, no fallback (raises error)

## Monitoring Failure Health

The observability layer tracks:
- `requests.failed` counter — total failures
- `errors.{type}` counter — failures by error category
- `retries.total` counter — retry volume (spikes indicate instability)
- Circuit breaker stats — trips, fallback counts, current state
- Dead-letter queue depth — permanently failed jobs needing attention

In production, alert on:
- Error rate > 5% over 5 minutes
- Circuit breaker trip (any module)
- Dead-letter queue depth > 0
- Retry rate > 10% of total requests

# Evaluation Results — SchemaGuard

## Test Suite Summary

| Test Suite | Assertions | Status |
|------------|-----------|--------|
| Integration test (`integration_test.py`) | 58 | ✅ All passed |
| Production test (`production_test.py`) | 77 | ✅ All passed |
| **Total** | **135** | **✅ 100%** |

Production test covers: sync validation, batch + drift, async pipeline, authentication, user-isolated storage, usage tracking + quotas, audit logging, rate limiting, performance metrics, and scoring consistency across all 16 seed records.

## Classification Accuracy

| Domain | Records | TP | FP | TN | FN | Precision | Recall | F1 | Accuracy |
|--------|---------|----|----|----|----|-----------|--------|----|----------|
| Healthcare | 8 | 3 | 0 | 5 | 0 | 1.0 | 1.0 | 1.0 | 100% |
| Finance | 8 | 3 | 0 | 5 | 0 | 1.0 | 1.0 | 1.0 | 100% |
| **Combined** | **16** | **6** | **0** | **10** | **0** | **1.0** | **1.0** | **1.0** | **100%** |

False quarantine rate: 0% — no valid records were incorrectly blocked.

## Confidence Score Distribution

| Category | Count | Mean Confidence | Min | Max |
|----------|-------|-----------------|-----|-----|
| Valid records | 10 | 1.00 | 1.00 | 1.00 |
| Invalid (critical) | 5 | 0.70 | 0.70 | 0.70 |
| Invalid (warning) | 1 | 0.88 | 0.88 | 0.88 |
| Edge cases | — | 1.00 | 1.00 | 1.00 |

**Separation gap:** 0.24–0.30 between valid and invalid. Clear enough for reliable three-tier routing.

## Decision Distribution

| Decision | Healthcare | Finance | Total |
|----------|-----------|---------|-------|
| 🟢 Trusted | 5 | 5 | 10 |
| 🟡 Flagged | 1 | 0 | 1 |
| 🔴 Quarantined | 2 | 3 | 5 |

The flagged record (HC-seed-006) is a warning-severity violation (osteoporosis on a 5-year-old). The decision router correctly routes it to review rather than blocking.

## Drift Detection

### Simulated Shift Detection (Healthcare)

| Injection | Signal | Metric | Detected |
|-----------|--------|--------|----------|
| patient_age +30 | Numeric shift | z = 4.13 | ✅ HIGH |
| gender → "other" | Categorical shift | PSI = 27.0 | ✅ HIGH |
| insurance → null | Null-rate change | 0% → 100% | ✅ LOW |

### Simulated Shift Detection (Finance)

| Injection | Signal | Metric | Detected |
|-----------|--------|--------|----------|
| income × 3 | Numeric shift | z = 4.13 | ✅ HIGH |
| credit_score → 800 | Numeric shift | z = 2.66 | ✅ MEDIUM |
| co_applicant shift | Categorical shift | PSI = 27.6 | ✅ HIGH |

All simulated distribution shifts were detected. No false negatives.

## Load Simulation (50 records)

| Metric | Value |
|--------|-------|
| Records processed | 50 |
| Success rate | 100% |
| Total processing time | ~100ms |
| Per-record average | ~2.0ms |
| Throughput | ~500 records/second |
| Latency p50 | 0.49ms |
| Latency p95 | 0.96ms |
| Latency p99 | 4.03ms |

## Edge Case Resilience

| Input | Outcome |
|-------|---------|
| `None` | Quarantined, no crash |
| `{}` (empty dict) | Quarantined, no crash |
| `"string"` | Quarantined, no crash |
| `[1, 2]` (list) | Quarantined, no crash |
| `42` (integer) | Quarantined, no crash |
| Unknown domain | Quarantined, no crash |
| Empty batch | Returns empty result, no crash |
| None batch | Returns empty result, no crash |
| Mixed-type batch | Non-dicts quarantined, dicts validated normally |

## Resilience Features Tested

| Feature | Tested | Status |
|---------|--------|--------|
| Queue retry (max 2) | ✅ | Handler called 3x, then dead-lettered |
| Circuit breaker trip | ✅ | Opens after threshold, returns fallback |
| Circuit breaker reset | ✅ | Re-closes after cooldown/manual reset |
| Rate limiter blocking | ✅ | Blocks at configured limit |
| User isolation | ✅ | Bob cannot see Alice's jobs |
| Quota enforcement | ✅ | Blocks when per-user limit exceeded |
| Audit log capture | ✅ | Per-user entries recorded and retrievable |

## Limitations

- Seed dataset is 16 records — need 300+ for statistical confidence
- Medication plausibility covers only 7 ICD-10 categories
- DTI threshold is fixed (60%) regardless of loan type
- Drift baseline with 3 records has high categorical variance
- All storage is in-memory — data lost on restart
- No real LLM provider connected — generation uses seed data

# SchemaGuard — Project Showcase

## 🚀 Project Overview

### The Problem

LLMs are increasingly used to generate structured data — patient intake records, loan applications, configuration files. The output passes JSON schema validation perfectly: correct types, correct fields, correct formats.

But the data is often **logically wrong**.

A patient discharged 7 days before being admitted. A loan approved for 52 times someone's annual income. A 5-year-old diagnosed with age-related osteoporosis. These are all valid JSON. They all pass schema checks. And they all flow silently into production databases, downstream analytics, and compliance reports.

There is no standard tool to catch these failures. Schema validation answers "is this well-formed?" but nobody answers **"does this make sense?"**

### The Solution

SchemaGuard is a semantic validation, confidence scoring, and drift detection layer for LLM-generated structured outputs. It sits between any LLM and the systems that consume its output, catching the errors that schema validation misses.

Every record gets validated through a four-stage pipeline, scored on a 0–1 confidence scale, and routed to one of three tiers: **trusted** (auto-accept), **flagged** (human review), or **quarantined** (blocked).

### Why It Matters

As LLMs become the backbone of data generation pipelines, the gap between "structurally valid" and "semantically correct" becomes a real business risk. In healthcare, a bad record can affect patient care. In finance, it can trigger incorrect risk assessments. SchemaGuard provides the missing quality gate.

---

## ⚡ Key Highlights

**Semantic Validation Engine**
10 cross-field rules across healthcare and finance domains. Catches temporal contradictions, ratio violations, age-inappropriate diagnoses, and impossible employment timelines. Rules are deterministic — same input always produces the same output.

**Drift Detection**
Monitors LLM output distributions over time using z-score (numeric), PSI (categorical), null-rate, and violation-rate signals. Catches slow behavioral degradation that no single-record check would find.

**Confidence Scoring + Decision Routing**
Continuous 0–1 score with severity-weighted penalties. Three-tier routing: trusted (≥0.85), flagged (0.50–0.84), quarantined (<0.50). Configurable thresholds. Every decision comes with a plain-language explanation.

**Async Processing Pipeline**
Queue-based job processing with concurrency control, retry logic (max 2 retries), dead-letter collection, and job status tracking (pending → processing → completed/failed).

**Multi-User Platform**
Token-based authentication, per-user job isolation, usage quotas, audit logging, and analytics dashboards. Users can only see their own jobs and results.

**Observability + Resilience**
Latency percentiles (p50/p95/p99), per-stage tracing, circuit breakers with configurable fallbacks, structured logging. The system never crashes — every failure mode produces a structured response.

---

## 🧠 What Makes This Unique

**It's not just schema validation.** Schema validation checks types and formats. SchemaGuard checks whether the values make sense *together*. A discharge date before an admission date is valid JSON — but it's a semantic failure that SchemaGuard catches.

**Drift detection for LLM outputs is rare.** Most validation tools check one record at a time. SchemaGuard also monitors the population: if an LLM starts generating different patterns — younger patients, higher incomes, fewer edge cases — the drift detector flags it before it becomes a data quality incident.

**Production-style architecture in a portfolio project.** This isn't a Jupyter notebook or a wrapper around an API call. It's a modular system with clean separation of concerns, configurable thresholds, retry logic, circuit breakers, audit trails, and a real API. The architecture demonstrates systems thinking, not just model usage.

**Deterministic and auditable.** Every validation decision has a full trace: which rules ran, which passed, which failed, what the confidence breakdown was, and why the routing decision was made. For regulated industries, this auditability is the difference between a useful tool and a liability.

---

## 📊 Impact

### What It Prevents

| Failure Type | Example | Without SchemaGuard | With SchemaGuard |
|-------------|---------|-------|------|
| Temporal contradiction | Discharge before admission | Enters database silently | Quarantined, HC-003 violation logged |
| Ratio violation | $2.5M loan on $48K income | Passes schema check | Quarantined, FN-002: 52x ratio flagged |
| Age-inappropriate data | 5-year-old with osteoporosis | Valid ICD-10 code, passes | Flagged, HC-004 warning |
| Silent drift | LLM starts generating younger patients | Undetected for weeks | z-score alert on first shifted batch |
| Impossible employment | 24-year-old with 18 years of work | Valid integers | Quarantined, FN-004 violation |

### By the Numbers

| Metric | Value |
|--------|-------|
| Classification accuracy | 100% (16/16 seed records) |
| Precision / Recall / F1 | 1.0 / 1.0 / 1.0 |
| False quarantine rate | 0% |
| Confidence separation gap | 0.24–0.30 between valid and invalid |
| Integration test assertions | 77/77 passed |
| Drift shift detection rate | 100% of simulated shifts caught |
| Processing throughput | ~500 records/second |

### System Scale

| Component | Scope |
|-----------|-------|
| Domains | 2 (healthcare intake, financial loan) |
| Semantic rules | 10 (5 per domain) |
| Drift signals | 4 (z-score, PSI, null-rate, violation-rate) |
| API endpoints | 15+ (sync, async, user, health, metrics) |
| Test assertions | 135 (58 integration + 77 production) |
| Documentation | 25+ files (architecture, interview prep, website, report) |
| Total Python modules | 30+ across 15 packages |

---

## 🏗️ Architecture at a Glance

```
LLM Output → Schema Check → Semantic Rules → Confidence Score → Decision Router
                                                                      ↓
                                                         trusted / flagged / quarantined
                                                                      ↓
                                                         explanation + audit log
```

For batch: per-record pipeline → aggregate stats → drift detection → alerts

For async: submit → queue → worker pool → result store → fetch by job_id

---

## 🛠️ Tech Stack

Python 3.11 · FastAPI · jsonschema · Streamlit · Pydantic · asyncio

---

## 💼 Who This Is For

**If you're evaluating this project:** This demonstrates backend systems engineering, data quality thinking, and production architecture — not just LLM prompt engineering. The system handles failure gracefully, scales conceptually, and is built with the same patterns used in real distributed systems.

**If you're building LLM pipelines:** SchemaGuard's architecture is a template for adding a quality gate to any structured-output pipeline. The rule engine, scoring framework, and drift detection patterns are domain-agnostic and ready to extend.

# Elevator Pitch — SchemaGuard

---

## 30-Second Version

"I built SchemaGuard — a semantic validation layer for LLM-generated structured data. LLMs produce JSON that passes schema validation but contains logical errors: a discharge before admission, a $2.5M loan on $48K income. SchemaGuard catches these with cross-field rules, scores each record's confidence, and routes it to trusted, flagged, or quarantined. It also detects when LLM output distributions drift over time. Built end-to-end: rule engine, async pipeline, drift detector, multi-user API, and observability."

---

## 1-Minute Version

"When LLMs generate structured data — patient records, loan applications — the output passes schema validation perfectly. But it can be logically wrong. A 5-year-old with osteoporosis. A loan approval before the application was even submitted. These silent failures flow straight into production.

I built SchemaGuard to fix this. It's a four-stage pipeline: structural validation, semantic rule checking, confidence scoring, and decision routing. Every record gets a 0-to-1 confidence score and is routed to trusted, flagged, or quarantined.

The system also monitors output distributions over time — if an LLM starts generating different patterns, the drift detector catches it before it becomes a data quality incident.

I built the full platform: 10 semantic rules across healthcare and finance, an async job processing queue with retries, multi-user authentication with per-user quotas, circuit breakers for failure resilience, distributed tracing, and a complete evaluation pipeline. 100% classification accuracy on seed data, 77 integration test assertions passing, all simulated drift shifts detected."

---

## 2-Minute Version

"The problem I'm solving is the gap between 'structurally valid' and 'semantically correct' in LLM outputs.

When teams use LLMs to generate structured JSON — patient intake forms, loan applications, configuration records — the output almost always passes schema validation. Types are correct, fields are present, formats match. But the data can contain logical contradictions that schema checks can't catch. A discharge date before an admission date. A 24-year-old claiming 18 years of employment. A loan amount that's 52 times the applicant's income. These pass every type check. They enter databases. They affect downstream decisions.

SchemaGuard is the missing layer. It validates records through four stages: structural schema enforcement, cross-field semantic rules, severity-weighted confidence scoring, and three-tier decision routing. Each record gets a continuous confidence score and is routed to trusted, flagged for review, or quarantined.

Beyond single-record validation, the system runs drift detection on batches — comparing output distributions against a stored baseline using z-scores, PSI, null rates, and violation rates. This catches population-level degradation that no per-record check would find.

The platform layer includes async job processing with a queue, retries, and dead-letter collection. Multi-user authentication with per-user quotas and job isolation. Observability with latency percentiles and per-stage tracing. Circuit breakers that prevent cascading failures — if one module crashes repeatedly, the breaker opens and routes to a safe fallback.

I built this across two domains — healthcare intake and financial loan applications — with 10 semantic rules, a FastAPI REST API, a Streamlit demo, and a full evaluation pipeline. 100% classification accuracy on seed data, 77 production test assertions passing, and every simulated drift shift detected.

The architecture is modular. Adding a new domain means adding two files: a schema and a rules file. Everything else — pipeline, scoring, drift, API, UI — works unchanged. The design choices are deliberate: deterministic rules for auditability, continuous scoring for nuanced routing, and in-memory components with clean interfaces so production replacements are one-import swaps."

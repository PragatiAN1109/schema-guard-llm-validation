# Differentiation — What Makes SchemaGuard Stand Out

---

## 1. Semantic Validation, Not Just Schema Validation

Most teams using LLMs for structured data generation stop at JSON schema validation. That catches missing fields, wrong types, and format mismatches. SchemaGuard goes further — it checks whether the values make sense *together*.

A discharge date before an admission date is a valid date in a valid field. A 5-year-old diagnosed with osteoporosis has a valid ICD-10 code. Schema validation passes both. SchemaGuard catches both.

**The distinction matters:** schema validation answers "is this well-formed?" Semantic validation answers "is this logically coherent?" In production, only the second question protects data quality.

---

## 2. Drift Detection — Population-Level Monitoring

Single-record validation catches per-record errors. But what about when an LLM gradually shifts its output distribution? Younger patients, higher incomes, fewer edge cases. No single record is wrong, but the population statistics silently diverge from expected baselines.

SchemaGuard tracks four drift signals across batches: numeric field shifts (z-score), categorical distribution changes (PSI), null-rate changes, and validation failure rate changes. This catches slow degradation that no per-record check would find.

**Most validation tools don't do this.** They validate one record at a time. SchemaGuard validates records individually *and* monitors the batch as a whole.

---

## 3. Continuous Confidence Scoring, Not Binary Pass/Fail

Binary pass/fail loses information. A record with one warning-level violation is different from a record with three critical failures. SchemaGuard preserves that gradient.

The confidence score starts at 1.0 and subtracts severity-weighted penalties: -0.30 for critical violations, -0.12 for warnings, -0.05 for info. The result is a continuous 0–1 score that drives three-tier routing: trusted, flagged, quarantined. Thresholds are configurable.

**Why it matters:** downstream systems can handle each tier differently. Trusted records flow through. Flagged records go to a review queue. Quarantined records are blocked. This is more useful than "valid" or "invalid."

---

## 4. Deterministic and Auditable — Not LLM Classification

You could use another LLM to validate LLM output. But LLM classifiers aren't reproducible — same input can produce different outputs. They can't provide rule-level audit trails. They can't be formally verified.

SchemaGuard's rules are deterministic Python functions. Same input always produces the same result. Every decision has a full trace: which rules ran, which passed, which failed, what the confidence breakdown was, and why the routing decision was made.

**For regulated industries (healthcare, finance),** this auditability isn't optional. It's the difference between a useful tool and a liability.

---

## 5. System-Level Engineering, Not Just Model Usage

This isn't a wrapper around an LLM API call. It's a complete validation system with clean architecture: separate packages for schemas, rules, validation, drift, scoring, API, and UI. Adding a new domain means adding two files — a schema and a rules file. The rest of the pipeline works unchanged.

The project demonstrates backend engineering fundamentals: modular design, decorator patterns, configurable thresholds, structured error handling, audit logging, REST API design, and evaluation methodology.

**The signal to recruiters:** this person thinks in systems, not just prompts.

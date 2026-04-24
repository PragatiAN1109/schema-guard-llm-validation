# Website Content — SchemaGuard

---

## Title

**SchemaGuard**

## Tagline

Catch the semantic errors that schema validation misses in LLM-generated structured outputs.

---

## Problem

When LLMs generate structured data — patient records, loan applications, configuration files — the output passes schema validation perfectly. Types are correct, required fields are present, formats match.

But the data can be **logically wrong**.

A patient discharged before being admitted. A loan approved for 52 times someone's income. A 5-year-old diagnosed with age-related osteoporosis. These are all valid JSON. They all pass schema checks. And they all flow silently into production databases.

There's no standard layer to catch these failures. SchemaGuard builds that layer.

---

## Solution

SchemaGuard validates LLM-generated JSON through three layers:

**Structural** — JSON Schema Draft 7 enforcement (types, formats, required fields, ranges)

**Semantic** — 10 cross-field rules checking logical consistency across related fields

**Monitoring** — drift detection comparing batch distributions against known-good baselines

Every record receives a **confidence score** (0–1) and a routing decision:

- 🟢 **Trusted** — passes all checks, safe for downstream use
- 🟡 **Flagged** — warnings detected, needs human review
- 🔴 **Quarantined** — critical failure, blocked from downstream

---

## Key Features

**Semantic Rule Engine** — 10 domain-specific cross-field rules with severity levels. Catches temporal contradictions, ratio violations, age-inappropriate diagnoses, and impossible employment timelines.

**Confidence Scoring** — weighted composite score that penalizes by violation severity. Configurable thresholds for routing decisions.

**Drift Detection** — tracks numeric (z-score), categorical (PSI), null-rate, and violation-rate shifts across batches. Alerts when LLM behavior changes.

**Human-Readable Explanations** — every flagged or quarantined record comes with a plain-language description of what went wrong.

**Audit Trail** — JSONL log per validation with timestamp, rules evaluated, results, and processing time.

**REST API** — FastAPI with Swagger docs. Single-record and batch endpoints.

**Interactive Demo** — Streamlit UI with validation, batch processing, and drift visualization.

---

## Architecture

```
JSON Record → Schema Check → Semantic Rules → Confidence Score → Decision
                                                                    ↓
                                                          trusted / flagged / quarantined
                                                                    ↓
                                                          explanation + audit log
```

For batches: per-record validation → aggregate stats → drift detection → alerts.

---

## Domains

| Domain | Rules | What Gets Caught |
|--------|-------|-----------------|
| Healthcare intake | HC-001 – HC-005 | Age/DOB mismatch, discharge before admission, adult diagnosis on a child, wrong medication for diagnosis |
| Financial loan | FN-001 – FN-005 | Approval before application, extreme loan-to-income, impossible employment length, approved exceeds requested |

---

## Results

Evaluated on 16 hand-labeled seed records (8 per domain).

| Metric | Value |
|--------|-------|
| Classification accuracy | 100% |
| Precision | 1.0 |
| Recall | 1.0 |
| F1 Score | 1.0 |
| False quarantine rate | 0% |
| Confidence gap (valid vs invalid) | 0.24 – 0.30 |

All simulated distribution shifts were detected by the drift module.

---

## Tech Stack

Python 3.11 · FastAPI · jsonschema · Streamlit · Pydantic · SQLite

---

## Future Work

- **RAG layer** for grounded explanations using retrieved rule documentation
- **LLM-generated datasets** at scale (300+ records per domain)
- **Additional domains** — e-commerce, insurance, API configurations
- **Production deployment** with Docker and CI/CD
- **Feedback loops** — use validation failures to correct LLM prompts

# Demo Script — SchemaGuard

**Duration:** 8–10 minutes
**Format:** Screen share with live system

---

## 1. Opening — The Problem (1 min)

"Imagine you're running an LLM pipeline that generates patient intake records or loan applications as structured JSON. Every record passes schema validation — correct types, correct fields, correct formats. But buried in the output is a healthcare record where the patient was discharged a week before they were admitted. Or a loan approval for 52 times someone's annual income.

These are **semantically invalid** records. They look right. They pass every type check. And they flow straight into your database without any alert.

SchemaGuard is the layer that catches them."

---

## 2. Why Schema Validation Isn't Enough (1 min)

"JSON Schema checks structure: are the right fields present, are the types correct, is a number within range. What it can't check is whether the values make *sense together*.

A discharge date before an admission date is a valid date in a valid field. A 5-year-old with an osteoporosis diagnosis has a valid ICD-10 code. Schema validation passes all of these.

SchemaGuard adds cross-field semantic rules, confidence scoring, and drift monitoring on top of schema validation. It doesn't replace schema checks — it completes them."

---

## 3. What SchemaGuard Does (1 min)

"Every record goes through a four-stage pipeline:

1. **Structural validation** — schema compliance
2. **Semantic validation** — 10 cross-field rules checking logical consistency
3. **Confidence scoring** — a 0-to-1 score based on what passed and what failed
4. **Decision routing** — trusted, flagged, or quarantined

The system supports two domains: healthcare intake and financial loan applications. Each has its own schema and its own set of semantic rules."

---

## 4. Architecture Overview (1 min)

"The system is modular Python. Schemas live in `schemas/`. Rules live in `rules/` — each rule is a decorated function registered in a domain-specific registry. The validator pipeline chains structural checks, semantic checks, scoring, and explanation into a single call.

For batch processing, the system also runs drift detection — comparing the current batch against a stored baseline using z-scores for numeric fields and PSI for categorical distributions.

There's a FastAPI REST API with Swagger docs, and a Streamlit UI for interactive demos."

---

## 5. Live Demo (4 min)

### 5a. Valid Record (~1 min)

*Open Streamlit UI. Select Healthcare domain. Paste the valid record (James Carter, pneumonia).*

"This is a standard healthcare intake record. 45-year-old male, admitted for pneumonia, discharged 5 days later, prescribed Azithromycin. Let's validate it."

*Click Validate.*

"Structural: pass. Semantic: pass. All 5 rules evaluated, all passed. Confidence score: 1.0. Decision: trusted. The explanation confirms no issues found."

### 5b. Invalid Record — Discharge Before Admission (~1.5 min)

*Paste the invalid record (Sarah Mitchell, discharge 2024-08-08, admission 2024-08-15).*

"Now here's a record that looks completely normal at first glance. Valid patient ID, valid diagnosis code, valid dates. But look closely — the discharge date is August 8th and the admission date is August 15th. The patient was discharged a week before being admitted."

*Click Validate.*

"Structural: pass — because every field has the right type. Semantic: fail — rule HC-003 caught the temporal contradiction. Confidence drops to 0.70. Decision: quarantined. The explanation says exactly what's wrong and which fields are involved.

This is the kind of silent failure that would pass schema validation in any production system."

### 5c. Batch Validation + Drift (~1.5 min)

*Switch to Batch Validation tab. Click run with seed data.*

"Running all 8 healthcare records through batch validation. The system processes each record through the full pipeline, then runs drift detection against the baseline.

Results: 5 trusted, 1 flagged, 2 quarantined. The flagged record is the osteoporosis-on-a-5-year-old — it's a warning-severity violation, so it gets flagged rather than quarantined. The two quarantined records have critical violations.

Mean confidence is 0.91. Processing time under 10ms for 8 records.

Drift detection checked 5 fields. No false alarms on the valid subset."

---

## 6. Confidence and Decision Logic (1 min)

"Confidence scoring starts at 1.0 and subtracts penalties. A critical violation costs 0.30. A warning costs 0.12. If the score is above 0.85 and everything passes, the record is trusted. Below 0.50 or with a critical violation at sub-trusted confidence, it's quarantined. Everything in between is flagged for review.

The key design choice: we don't just give a binary pass/fail. We give a continuous score and a three-tier decision, so downstream systems can decide how to handle each tier. A quarantined record might trigger manual review. A flagged record might go into a review queue. A trusted record flows through automatically."

---

## 7. Key Takeaway (30 sec)

"SchemaGuard fills the gap between schema validation and semantic correctness. It's deterministic, auditable, and interpretable — no black-box LLM classification. Every decision has a rule trace, a confidence breakdown, and a human-readable explanation.

For any team using LLMs to generate structured data, this is the validation layer that's missing."

---

## Backup Q&A Points

**Q: Why not just use an LLM to validate?**
A: LLMs hallucinate. For compliance-critical validation, you need deterministic rules with an audit trail. SchemaGuard's rules are reproducible — same input always produces same output.

**Q: How does drift detection work?**
A: We build a statistical baseline from known-good records. For each new batch, we compare distributions using z-scores for numeric fields and PSI for categorical fields. If the shift exceeds a threshold, we raise an alert.

**Q: Can this scale?**
A: The validation pipeline processes 8 records in under 10ms. It's pure Python with no external dependencies at runtime. For production scale, you'd add async processing and a proper queue, but the core logic is fast.

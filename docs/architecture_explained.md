# Architecture Explained — SchemaGuard

A verbal walkthrough of how the system works, suitable for interviews and design discussions.

---

## How Data Flows Through the System

A JSON record enters the system with a domain tag — either "healthcare_intake" or "financial_loan_application." The domain determines which schema and which rules apply.

**Step 1: Structural validation.** The record is checked against a JSON Schema Draft 7 definition. This catches missing required fields, wrong types (string where integer is expected), values outside allowed ranges, and pattern mismatches (like an ICD-10 code that doesn't match the expected format). If structural validation fails, the pipeline stops here — there's no point running semantic checks on a record that can't even satisfy the schema.

**Step 2: Semantic validation.** If the record is structurally valid, all registered rules for that domain execute. Each rule is a Python function that takes the record as a dictionary and checks a cross-field relationship. For example, HC-003 parses the admission_date and discharge_date, converts them to date objects, and checks that discharge is on or after admission. Every rule returns a structured result: rule ID, pass/fail, severity (critical or warning), the fields involved, and a human-readable message. All rules run — there's no short-circuiting. A single record can have multiple violations.

**Step 3: Confidence scoring.** The results from both validation stages feed into a confidence scorer. It starts at 1.0 and subtracts penalties: 0.30 per critical violation, 0.12 per warning, 0.05 per info-level issue. If no semantic rules could run (structurally invalid), the score is 0.0. The output is a float between 0 and 1 that represents how much the system trusts this record.

**Step 4: Decision routing.** The confidence score maps to a three-tier decision. 0.85 or above with all checks passing → trusted. Between 0.50 and 0.85, or with non-critical warnings at high confidence → flagged for human review. Below 0.50, or with a critical violation and sub-trusted confidence → quarantined. The router also checks for specific conditions — a critical violation at any confidence below trusted forces quarantine.

**Step 5: Explanation generation.** The explanation builder takes the structural and semantic results and produces a plain-language summary. It groups violations by severity, references specific field values, and adds the routing decision as context. This is what gets displayed in the UI and returned in the API.

**Step 6: Audit logging.** Every validation run writes a JSONL entry with the timestamp, record ID, domain, structural and semantic results, confidence score, decision, which rules were evaluated, which rules were violated, and processing time in milliseconds.

---

## How Batch Processing and Drift Work

For batch mode, each record goes through the same pipeline individually. After all records are processed, the system aggregates: how many trusted, flagged, quarantined, what's the mean confidence, total processing time.

Then drift detection runs. The system loads a baseline profile (generated previously from known-good records) and compares the current batch's distributions. For numeric fields like patient_age or annual_income, it computes a z-score — how many standard deviations has the mean shifted. For categorical fields like gender or loan_purpose, it computes PSI — the Population Stability Index, which measures how much the distribution has changed. It also tracks null rates and overall violation rates.

If any metric exceeds its threshold (z > 1.5 for numeric, PSI > 0.20 for categorical, 15% for null rates, 10% for violation rates), an alert is raised with a severity level and a message describing the shift.

---

## Why These Design Choices

**Decorator-based rule registry.** Rules are just Python functions with a `@register_rule` decorator. Adding a new rule is one function — no configuration files, no separate registration step. The registry groups rules by domain, so the pipeline only runs rules relevant to the current record type.

**Severity levels, not binary pass/fail.** A 5-year-old with osteoporosis (HC-004, warning) is different from a discharge before admission (HC-003, critical). The severity distinction flows into confidence scoring and routing, allowing nuanced downstream handling.

**Continuous confidence score.** Binary pass/fail loses information. A record with one warning is different from a record with three critical violations. The confidence score preserves that gradient, and configurable thresholds let teams tune the routing to their risk tolerance.

**Deterministic rules, not LLM classification.** For validation in regulated industries (healthcare, finance), reproducibility matters. Same input always produces the same output. Every decision has a full rule trace. An LLM classifier might achieve similar accuracy but can't provide the same auditability.

**Modular architecture.** Schemas, rules, validator, drift, scoring, API, and UI are all separate packages with clean interfaces. Adding a third domain means adding two files (schema + rules) — the pipeline, scoring, drift, API, and UI work unchanged.

**Drift detection as a separate signal.** Single-record validation catches per-record issues. Drift detection catches population-level shifts that no single record would trigger. Together, they cover both granular and systemic quality failures.

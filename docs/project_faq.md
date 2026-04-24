# Project FAQ — SchemaGuard

Concise answers to common interview and presentation questions.

---

**Why did you build this?**

I noticed that teams using LLMs for structured data generation rely entirely on JSON schema validation. That catches type errors but misses logical contradictions — a discharge before admission, a loan amount that's 50x income. These silent failures are a real problem in production. I wanted to build the missing layer between schema checks and data quality.

---

**How is this different from JSON schema validation?**

JSON schema checks structure: types, required fields, formats, ranges. SchemaGuard checks semantics: whether field values are logically consistent with each other. A discharge date before an admission date passes schema validation because both are valid dates. SchemaGuard catches it because it checks the cross-field relationship.

---

**How does the rule engine work?**

Each rule is a Python function registered with a decorator that specifies the domain, rule ID, severity, and affected fields. At validation time, all rules for the record's domain execute. Each returns a structured result — pass/fail, severity, fields involved, and a message. Rules don't short-circuit; a single record can have multiple violations.

---

**How do you compute the confidence score?**

Start at 1.0. Subtract 0.30 for each critical violation, 0.12 for each warning, 0.05 for info-level issues. If drift is detected in batch mode, subtract 0.03 per alert up to a cap. The result is clamped to 0–1. Structural failure immediately floors the score to 0.0.

---

**How does the decision routing work?**

Three tiers based on confidence and violation severity. Above 0.85 with all checks passing → trusted. Between 0.50 and 0.85, or with non-critical warnings → flagged for review. Below 0.50, or with a critical violation at sub-trusted confidence → quarantined. Thresholds are configurable via environment variables.

---

**How do you detect drift?**

I build a baseline profile from known-good records — means, standard deviations, and frequency distributions per field. For each new batch, I compare distributions. Numeric fields use z-score normalized mean shift (alert if z > 1.5). Categorical fields use Population Stability Index (alert if PSI > 0.20). I also track null-rate changes and validation failure rates.

---

**What domains does it support?**

Healthcare intake and financial loan applications. Healthcare rules check temporal consistency (dates), age-diagnosis plausibility, and medication-diagnosis compatibility. Finance rules check date ordering, loan-to-income ratios, debt-to-income ratios, employment length vs. age, and approved vs. requested amounts.

---

**Can you add a new domain easily?**

Yes. Add a JSON schema file in `schemas/` and a rules file in `rules/`. The validation pipeline, scoring, drift detection, API, and UI all work unchanged. The architecture is domain-agnostic by design.

---

**What are the limitations?**

The seed dataset is small — 16 hand-labeled records. The metrics are perfect on that set but need validation against larger LLM-generated datasets for statistical significance. The medication plausibility rule only covers 7 ICD-10 categories. The DTI rule uses a fixed threshold that doesn't account for loan type. Drift detection baseline needs more records to reduce false alarms on categorical fields.

---

**What would you improve?**

Three things. First, generate 300+ records per domain using the prompt templates to get statistically meaningful evaluation metrics. Second, add a lightweight RAG layer — store rule documentation in a vector store and use retrieved context to ground explanation-generation prompts. The architecture is ready for it. Third, containerize with Docker and add CI/CD for production deployment.

---

**Why deterministic rules instead of using an LLM to validate?**

Reproducibility and auditability. In healthcare and finance, you need the same input to always produce the same output, with a full trace of which rules ran and which failed. LLM classifiers are non-deterministic, can't provide rule-level audit trails, and are harder to formally verify. Deterministic rules are the right tool for compliance-critical validation.

---

**How fast is it?**

The validation pipeline processes 8 records in under 10ms, including structural validation, semantic rule execution, confidence scoring, decision routing, explanation generation, and audit logging. It's pure Python with no external service calls at runtime.

---

**What's the tech stack?**

Python 3.11, FastAPI for the REST API, jsonschema Draft 7 for structural validation, a custom decorator-based rule registry for semantic checks, Streamlit for the demo UI, and JSON/SQLite for storage. Drift detection uses standard statistical metrics (z-score, PSI). No ML models in the validation loop.

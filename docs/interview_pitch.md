# Interview Pitch — SchemaGuard

---

## 60-Second Version

"I built SchemaGuard, a semantic validation layer for LLM-generated structured outputs. The problem: when LLMs generate JSON records — patient intake forms, loan applications — the output passes schema validation but can contain logical contradictions. A discharge date before an admission date, a loan amount that's 50x someone's income. These silent failures flow into databases without any alert.

SchemaGuard adds cross-field semantic rules on top of schema validation. It checks that fields are consistent with each other, assigns a confidence score, and routes records to trusted, flagged, or quarantined. It also monitors output distributions over time so you can detect when an LLM's behavior shifts.

I built it end-to-end — rule engine, validation pipeline, drift detection, REST API, Streamlit demo, evaluation pipeline. Two domains: healthcare and financial. 10 semantic rules, 100% classification accuracy on seed data, with clear confidence separation between valid and invalid records."

---

## 2-Minute Version

"The project started from a real gap I noticed: teams deploying LLMs for structured data generation rely entirely on JSON schema validation. That catches type errors and missing fields, but it misses logical errors. A healthcare record where a 5-year-old patient is diagnosed with age-related osteoporosis passes every schema check. A loan approved for 52 times someone's income clears every type constraint. These are semantic failures, and there's no standard lightweight tool to catch them.

SchemaGuard fills that gap. It's a Python system with a multi-stage validation pipeline. First, it runs structural validation against JSON Schema Draft 7. If that passes, it runs semantic validation — 10 cross-field rules across healthcare and finance domains. Rules like 'discharge date must be after admission date,' 'stated age must match the computed age from date of birth,' 'loan-to-income ratio must be within 10x.' Each rule is a registered function with a severity level.

After validation, the system computes a confidence score — starts at 1.0, subtracts penalties based on violation severity. Then it routes the record: above 0.85 is trusted, 0.50 to 0.84 is flagged for review, below 0.50 is quarantined. Every decision comes with a human-readable explanation and an audit log entry.

For batch processing, there's also drift detection. The system builds a baseline profile from known-good records and compares new batches using z-scores for numeric fields and PSI for categorical distributions. If the LLM starts generating different patterns — younger patients, higher incomes, fewer edge cases — the drift detector raises an alert.

I built a FastAPI REST API, a Streamlit demo UI, and a full evaluation pipeline with precision, recall, F1, and false-quarantine rate. On 16 labeled seed records, the system achieves 100% classification accuracy with zero false quarantines and clear confidence separation between valid and invalid records.

The architecture is modular — schemas, rules, validator, drift, and scoring are all separate packages. Adding a new domain means adding a schema file and a rules file. The rest of the pipeline works unchanged."

---

## Key Talking Points

### Semantic Validation vs. Schema Validation
"Schema validation checks types, formats, and required fields. Semantic validation checks whether the values make sense *together*. A discharge date before an admission date is a valid date in a valid field — but it's logically impossible. SchemaGuard catches these cross-field contradictions."

### Rule Engine Design
"I used a decorator-based registry pattern. Each rule is a Python function that takes a record and returns a structured result — rule ID, pass/fail, severity, affected fields, and a message. Rules are registered per domain. At validation time, all rules for the domain run and violations are collected without short-circuiting."

### Confidence Scoring
"Rather than binary pass/fail, I compute a continuous confidence score. This lets downstream systems make nuanced decisions. A record with one warning-level violation might score 0.88 and get flagged for review, while a record with a critical violation scores 0.70 and gets quarantined. The scoring weights are configurable."

### Drift Detection
"In production, LLM output quality can degrade gradually — prompt changes, model updates, temperature drift. The drift detector compares batch statistics against a baseline using z-scores for numeric distributions and Population Stability Index for categorical fields. This catches slow degradation that no single-record check would find."

### Why Deterministic Rules, Not LLM Classification
"For compliance-critical use cases — healthcare, finance — you need reproducibility and auditability. An LLM classifier might catch the same errors, but its decisions aren't reproducible, aren't explainable in the same way, and can't be audited with a rule trace. SchemaGuard's decisions are deterministic: same input, same output, full trace."

### Technical Depth (if asked)
"The pipeline is: jsonschema Draft 7 for structural validation, a custom rule registry with decorator-based registration, severity-weighted confidence scoring with configurable thresholds, and a decision router with explicit reasoning. Drift uses z-score normalized mean shift for numeric fields, PSI for categorical fields, plus null-rate and violation-rate tracking. The API is FastAPI with Pydantic models. The UI is Streamlit with three tabs — single validation, batch with drift, and a seed data browser."

---

## If Asked: "What Would You Improve?"

"Three things. First, the seed dataset is small — 16 hand-labeled records. The architecture supports LLM-generated datasets at scale, but I'd want 300+ records per domain for statistically meaningful metrics. Second, I'd add a lightweight RAG layer — store rule documentation in a vector store and use retrieved context to ground the explanation-generation prompts. The architecture is ready for it; I just scoped it out of the MVP. Third, for production, I'd containerize with Docker, add CI/CD, and deploy behind proper auth."

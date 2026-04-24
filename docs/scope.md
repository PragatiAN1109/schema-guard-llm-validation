# Scope

## MVP

- **Synthetic data generation** — LLM-driven generation of labeled valid, invalid, and edge-case records using prompt engineering
- **Schema validation** — JSON schema enforcement for both domains (types, required fields, formats, enums)
- **Semantic rule engine** — Cross-field validation rules per domain, registered against a common engine interface
- **Drift detection** — Baseline profiling and statistical drift alerting (PSI / JS divergence)
- **Confidence scoring** — Composite score (0–1) combining structural, semantic, and anomaly signals
- **Routing logic** — Trusted / flagged / quarantined decision per record
- **Audit logging** — Structured JSON log entry for every validation run
- **Demo UI** — Streamlit app for single-record validation with domain selection
- **Evaluation datasets** — 250–400 labeled records per domain

## Deferred

- Batch validation UI
- Configurable threshold files (YAML/JSON)
- Dashboard-style metrics view with drift charts
- Enhanced explanation formatting with severity levels
- Lightweight RAG for grounded explanations (optional future enhancement)

## Out of Scope

- Multi-user authentication or role-based access
- Full production deployment (containers, cloud, CI/CD)
- Advanced agent orchestration or multi-step LLM workflows
- Fine-tuning a custom model
- Real-time distributed streaming architecture
- More than two domains
- Integration with external EHR, banking, or compliance systems

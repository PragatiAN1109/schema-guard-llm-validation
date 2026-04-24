# Resume Bullet Points — SchemaGuard

Use these for software engineering, backend, or ML/AI-adjacent roles. Pick 4–5 that best match the job description.

---

## Primary Bullets

- **Designed and built SchemaGuard**, a semantic validation layer for LLM-generated structured outputs that detects cross-field contradictions, computes confidence scores, and routes records to trusted/flagged/quarantined — achieving 100% classification accuracy across healthcare and finance domains

- **Engineered a 10-rule semantic validation engine** using a decorator-based registry pattern, catching silent failures in LLM outputs that pass JSON schema validation — including temporal contradictions, ratio violations, and age-inappropriate medical diagnoses

- **Implemented a multi-signal drift detection system** that monitors LLM output distributions using z-score normalized mean shift, Population Stability Index (PSI), null-rate tracking, and violation frequency analysis to detect behavioral degradation across batches

- **Built a severity-weighted confidence scoring pipeline** that combines structural validation, semantic rule results, and drift signals into a composite 0–1 score with configurable routing thresholds, producing clear separation between valid (1.0) and invalid (0.70) records

- **Developed a full-stack validation platform** with a FastAPI REST API (4 endpoints, Pydantic models, Swagger docs), Streamlit demo UI (single + batch validation with drift alerts), and an automated evaluation pipeline computing precision, recall, F1, and false-quarantine rate

- **Created a prompt engineering framework** with 7 template families to generate labeled synthetic datasets — valid, semantically invalid, and edge-case records — with controlled error injection and difficulty levels across healthcare intake and financial loan application domains

---

## Alternate Phrasings (shorter)

- Built a semantic compliance layer for LLM outputs with 10 cross-field rules, confidence scoring, and drift detection — 100% accuracy on evaluation data with zero false quarantines

- Designed a multi-stage validation pipeline (schema → semantic → scoring → routing) for LLM-generated JSON, deployed as a FastAPI service with Streamlit UI

- Implemented drift detection for LLM output monitoring using z-score and PSI metrics, detecting all simulated distribution shifts in healthcare and finance domains

---

## For Specific Role Types

**Backend / Systems:**
- Architected a modular Python validation system with clean separation of concerns — schemas, rules, validator, drift, scoring as independent packages with decorator-based registration and configurable thresholds

**Data / ML Engineering:**
- Built a data quality monitoring system for LLM outputs with baseline profiling, distribution drift detection, and automated flagging — processing 8 records in under 10ms with full JSONL audit trails

**Full Stack:**
- Delivered an end-to-end LLM output validation platform: Python backend (FastAPI), interactive demo (Streamlit), REST API with Swagger docs, evaluation pipeline with HTML chart generation, and a project website

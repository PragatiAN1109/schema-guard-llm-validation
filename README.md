# SchemaGuard

> **LLMs generate structurally valid JSON that is semantically wrong. SchemaGuard catches what schema validation misses.**

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/api-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/tests-137%20passing-brightgreen.svg)](#tests)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Course](https://img.shields.io/badge/course-INFO%207375-orange.svg)](https://northeastern.edu)

**Semantic validation and drift detection for LLM-generated structured outputs.**  
Built for INFO 7375 — Prompt Engineering for Generative AI · Northeastern University.

---

## The Problem

When LLMs generate structured data — patient records, loan applications — the output passes JSON schema validation perfectly. But the data can be logically broken:

| Record | What's wrong | Passes jsonschema? |
|--------|-------------|-------------------|
| Patient discharged 7 days before admission | `discharge_date < admission_date` | ✅ Yes |
| Loan for 52× the applicant's income | `loan_amount / income = 52` | ✅ Yes |
| 5-year-old diagnosed with osteoporosis | Adult-only ICD-10 code M81.0 | ✅ Yes |

Every one flows silently into production. **SchemaGuard stops them.**

---

## How It Works

Every record passes through a **four-stage pipeline**:

```
JSON Record
    ↓
[1] Structural Validation    JSON Schema Draft 7 (types, formats, required fields)
    ↓
[2] Semantic Validation      10 cross-field rules (temporal, ratio, plausibility)
    ↓
[3] Confidence Scoring       score = 1.0 − 0.30×critical − 0.12×warning
    ↓
[4] Decision Router          trusted ≥ 0.85 / flagged 0.50–0.84 / quarantined < 0.50
```

For batches, **drift detection** monitors population-level shifts using z-scores, PSI, null-rate, and violation-rate tracking.

**RAG-enhanced explanations** retrieve regulatory context (CMS, HL7 FHIR, CFPB ATR, ICD-10) and generate grounded, actionable explanations — going from *"this field is wrong"* to *"here's the regulation it violates and how to fix it."*

---

## Quick Start (3 commands)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key (required for RAG explanations + document ingest)
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# 3. Start the API
uvicorn api.main:app --reload --port 8000
# → API docs: http://localhost:8000/docs
```

Try a validation immediately:

```bash
curl -s -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "healthcare_intake",
    "record": {
      "patient_id": "P-4412", "first_name": "Sarah", "last_name": "Mitchell",
      "date_of_birth": "1990-01-20", "gender": "female",
      "admission_date": "2024-08-15", "discharge_date": "2024-08-08",
      "diagnosis_code": "N39.0", "medication": "Ciprofloxacin",
      "patient_age": 34, "emergency_admission": false
    }
  }' | python3 -m json.tool
```

Expected: `"decision": "flagged"`, `"confidence_score": 0.7`, `HC-003` violation.

---

## Features

| Feature | Description | Endpoint |
|---------|-------------|----------|
| **Single validation** | Structural + semantic + confidence + routing | `POST /validate` |
| **Batch validation** | N records + drift detection | `POST /batch-validate` |
| **Async pipeline** | Job queue with retry + dead-letter | `POST /async/submit` |
| **RAG explanations** | Regulation-grounded failure explanations | `POST /rag/explain` |
| **Document ingest** | Upload PDF/text → extract JSON → validate | `POST /ingest/upload` |
| **Drift detection** | z-score + PSI + null-rate + violation-rate | included in batch |

---

## Semantic Rules

### Healthcare Intake (HC-001 – HC-005)

| Rule | Check | Severity |
|------|-------|----------|
| HC-001 | `patient_age` matches computed age from DOB + admission date | Critical |
| HC-002 | `admission_date ≥ date_of_birth` | Critical |
| HC-003 | `discharge_date ≥ admission_date` | Critical |
| HC-004 | Diagnosis code is age-appropriate (ICD-10-CM edit table) | Warning |
| HC-005 | Medication is clinically plausible for the diagnosis | Warning |

### Financial Loan Application (FN-001 – FN-005)

| Rule | Check | Severity |
|------|-------|----------|
| FN-001 | `approval_date ≥ application_date` | Critical |
| FN-002 | `loan_amount / annual_income ≤ 10×` | Critical |
| FN-003 | `existing_debt / annual_income ≤ 60%` | Warning |
| FN-004 | `employment_length_years ≤ (age − 16)` | Critical |
| FN-005 | `approved_amount ≤ loan_amount` | Critical |

---


## Evaluation Results

Evaluated on 16 labeled seed records + 140 real audit-log records.

| Metric | Value |
|--------|-------|
| Precision / Recall / F1 | **1.0 / 1.0 / 1.0** (both domains) |
| Accuracy | **100%** |
| False quarantine rate | **0%** |
| Median validation latency | **0.09 ms** |
| Throughput | **~3,800 records/second** |
| Confidence gap (valid vs invalid) | **+0.24 HC / +0.30 FN** |
| RAG explanation quality | **6.0/6** (vs 2.7/6 baseline) |
| Integration tests | **58/58 passing** |
| Production tests | **79/79 passing** |

---

## Project Structure

```
schema-guard-llm-validation/
├── validator/          Core pipeline: structural → semantic → scoring → routing
├── rules/              Rule registry + 10 domain-specific decorated functions
├── schemas/            JSON Schema Draft 7 for both domains
├── scoring/            Confidence scorer + decision router
├── drift/              Baseline profiler + 4-signal drift detector
├── rag/                FAISS vector store + RAG explainer + API routes
├── ingest/             Document upload → LLM extraction → validation
├── api/                FastAPI standalone (all 5 routers, this is the main entry)
├── backend/            Production FastAPI + SQLite (dashboard + Next.js backend)
├── frontend/           Next.js 14 dashboard (6 pages)
├── data_gen/           Synthetic dataset generator (600 records, quality-gated)
├── evaluation/         Tests (137 assertions) + 12 charts + metrics JSON/CSV
├── notebooks/          6 Jupyter notebooks (02/03/04 fully executed)
├── outputs/plots/      20 presentation-ready charts
├── website/            Self-contained HTML/CSS/JS (GitHub Pages ready)
├── docs/               Academic report, video demo script, architecture docs
└── audit_logs/         JSONL validation history (140 real records)
```

---

## Running Other Components

### Frontend dashboard (Next.js)
```bash
cd frontend && npm install && npm run dev
# → http://localhost:3000
```

### Streamlit demo UI
```bash
streamlit run ui/app.py
```

### Build RAG index (one-time, ~10 seconds)
```bash
python3 rag/vector_store.py --build
```

### Run all tests
```bash
python3 -m evaluation.integration_test   # 58 assertions
python3 -m evaluation.production_test    # 79 assertions
```

### Regenerate all evaluation charts
```bash
python3 evaluation/generate_full_metrics.py
```

### Generate synthetic dataset (requires API key)
```bash
./generate_dataset.sh --dry-run   # confirm plan first
./generate_dataset.sh             # generate 600 records
```

### Document ingest (upload PDF → extract → validate)
```bash
# Via API (server must be running)
curl -X POST http://localhost:8000/ingest/upload \
  -F "file=@patient_record.pdf" \
  -F "domain=healthcare_intake"

# Via CLI (no server needed)
python3 ingest/test_ingest.py --domain healthcare_intake
```

---

## Notebooks

| Notebook | Topic | Status |
|----------|-------|--------|
| `01_prompt_engineering.ipynb` | Prompt template design, v1→v3 iteration | Contains outputs |
| `02_validation_pipeline.ipynb` | 4-stage pipeline walkthrough, 16 seed records | **Fully executed** |
| `03_evaluation_metrics.ipynb` | All 12 evaluation charts + metrics tables | **Fully executed** |
| `04_drift_detection.ipynb` | Baseline profiling, drift signals | **Fully executed** |
| `05_synthetic_data_generation.ipynb` | Dataset generator walkthrough | Add API key to run |
| `06_rag_explanations.ipynb` | FAISS demo, baseline vs RAG comparison | Add API key to run |

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service status |
| `GET` | `/example` | Sample request payloads |
| `POST` | `/validate` | Single record validation |
| `POST` | `/batch-validate` | Batch + drift detection |
| `POST` | `/async/submit` | Submit async job |
| `POST` | `/async/process` | Process queue |
| `GET` | `/async/result/{id}` | Get job result |
| `POST` | `/rag/explain` | Validate + RAG explanation |
| `GET` | `/rag/status` | Check FAISS index |
| `POST` | `/rag/search` | Search knowledge base |
| `POST` | `/ingest/upload` | Upload document → extract → validate |
| `GET` | `/ingest/supported-domains` | List supported domains |

Full Swagger docs at `http://localhost:8000/docs`.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Core language | Python 3.12 |
| API framework | FastAPI + Pydantic v2 |
| Frontend | Next.js 14 · React 18 · Tailwind CSS |
| Database | SQLite (dev) → PostgreSQL (prod) |
| LLM | Claude claude-opus-4-5 (Anthropic) |
| Vector store | FAISS IndexFlatIP (cosine, 384-dim) |
| Embeddings | `all-MiniLM-L6-v2` (sentence-transformers) |
| Schema validation | jsonschema Draft 7 |
| PDF extraction | pdfplumber → pypdf |
| Drift detection | z-score + PSI + null-rate + violation-rate |
| Auth | Token-based header auth |
| Resilience | Circuit breakers (3 modules) + dead-letter queue |
| Observability | Latency histograms + distributed tracing |
| Tests | pytest (137 assertions) |

---

## Tests

```
Tests                                    Assertions
─────────────────────────────────────────────────────
evaluation/integration_test.py               58 / 58
evaluation/production_test.py                79 / 79
─────────────────────────────────────────────────────
Total                                       137 / 137  ✓
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*SchemaGuard · Pragati Narotam · INFO 7375 Prompt Engineering for GenAI · Northeastern University · 2025*

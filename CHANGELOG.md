# Changelog

All notable changes to SchemaGuard are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.3.0] — 2025-04-19

### Added
- **Document Ingest feature** (`ingest/`) — upload PDF or plain-text, extract structured JSON with Claude, validate through SchemaGuard in a single API call
  - `POST /ingest/upload` — multipart form upload endpoint
  - `GET /ingest/supported-domains` — lists supported domains and file types
  - `ingest/test_ingest.py` — CLI smoke-test with built-in fixtures
- **pyproject.toml** — proper package metadata for the project
- **CHANGELOG.md** — this file

### Changed
- `requirements.txt` — rewritten to include all actual dependencies with minimum versions: `fastapi`, `python-multipart`, `faiss-cpu`, `sentence-transformers`, `pdfplumber`, `pypdf`
- `.gitignore` — updated to exclude FAISS store, model caches, generated datasets, `.env` properly
- `api/main.py` — mounts `ingest_router` at `/ingest`
- `evaluation/results/` — removed stale `.html` artefacts; added `README.md`

### Fixed
- Notebooks 02/03/04 now fully executed with baked-in cell outputs
- `evaluation/results/` cleaned of stale HTML files

---

## [0.2.0] — 2025-04-18

### Added
- **RAG Explanation Module** (`rag/`)
  - 11 synthetic reference documents (CMS, HL7 FHIR, ICD-10, CFPB ATR, Reg Z, ECOA, OCC)
  - FAISS `IndexFlatIP` vector store with `all-MiniLM-L6-v2` embeddings (17 chunks, 384-dim)
  - `POST /rag/explain` — full RAG pipeline: validate → retrieve → augment → generate
  - `GET /rag/status` and `POST /rag/search` debug endpoints
  - RAG evaluation: 2.7/6 baseline → 6.0/6 RAG quality score across 6 test cases
- **Full Evaluation Suite** (`evaluation/generate_full_metrics.py`)
  - 12 presentation-ready plots in `outputs/plots/`
  - `evaluation/results/full_metrics_report.json` and `metrics_table.csv`
- **Project Website** (`website/index.html`) — 1,600-line self-contained HTML/CSS/JS, GitHub Pages ready
- **Academic Report** (`docs/report/SchemaGuard_Report.pdf` + `.md`) — 10-section report
- **Video Demo Script** (`docs/demo/VIDEO_SCRIPT.pdf` + `.md`) — fully timed 10-minute script
- **Notebooks 05 and 06** — synthetic data generation and RAG explanations

### Changed
- `evaluation/generate_full_metrics.py` — reads real audit-log data (140 records)
- All 6 notebooks now have full content and structure

---

## [0.1.0] — 2025-04-04

### Added
- **Core validation pipeline** (`validator/`) — structural → semantic → confidence → routing
- **10 semantic rules** across two domains:
  - Healthcare Intake: HC-001 (age), HC-002 (admit after birth), HC-003 (discharge after admit), HC-004 (age-appropriate Dx), HC-005 (medication plausibility)
  - Financial Loan Application: FN-001 (approval after application), FN-002 (loan:income ≤ 10×), FN-003 (DTI ≤ 60%), FN-004 (employment age check), FN-005 (approved ≤ requested)
- **Confidence scoring** — severity-weighted penalty formula (critical −0.30, warning −0.12)
- **Decision routing** — trusted / flagged / quarantined with configurable thresholds
- **Drift detection** (`drift/`) — z-score + PSI + null-rate + violation-rate signals
- **FastAPI REST API** (`api/`) — `/validate`, `/batch-validate`, `/async/*`, `/user/*`
- **Production backend** (`backend/`) — FastAPI + SQLite with dashboard endpoint
- **Next.js 14 frontend** (`frontend/`) — 6 pages: dashboard, validate, batch, rules, audit, use cases
- **Streamlit UI** (`ui/`) — interactive single-record validation demo
- **Synthetic data generator** (`data_gen/`) — 300 records per domain with quality gates
- **Integration tests** — 58 assertions passing
- **Production tests** — 79 assertions passing
- **Audit logging** — JSONL per-record trace (`audit_logs/`)
- **Resilience** — circuit breakers (drift, semantic, storage) with fallback
- **Observability** — latency histograms + distributed tracing
- **Auth** — token-based API authentication
- **Notebooks 01–04** — prompt engineering, pipeline walkthrough, evaluation, drift detection

# SchemaGuard — Complete Project Summary for Peer Review
**Author:** Pragati Narotam  
**Course:** INFO 7375 — Prompt Engineering for Generative AI, Northeastern University  
**Repository:** github.com/pragatinarote/schema-guard-llm-validation  
**Stack:** Python 3.12 · FastAPI · Next.js 14 · FAISS · Claude (Anthropic)

---

## 1. WHAT THE PROJECT IS

SchemaGuard is a **semantic validation and drift detection system** for LLM-generated structured JSON data. It addresses a specific, narrow problem: LLMs that generate structured records (patient intake forms, loan applications) reliably produce JSON that passes schema validation but is logically inconsistent across fields.

**The core insight:** JSON Schema Draft 7 checks whether a field has the right type and format. It cannot check whether two fields are mutually consistent. SchemaGuard adds that second layer.

Three motivating examples that all pass jsonschema validation:
- A patient discharged 7 days *before* being admitted (`discharge_date < admission_date`)
- A loan for $2.5M on $48K income (52× loan-to-income ratio)
- A 5-year-old diagnosed with age-related osteoporosis (ICD-10 code M81.0, adult-only)

The project was built for a Prompt Engineering course, so it also demonstrates: structured prompting for synthetic data generation, RAG-enhanced LLM explanations, and the engineering tradeoffs in building reliable AI-adjacent systems.

---

## 2. PROBLEM BEING SOLVED

### 2.1 The Gap in Existing Tools
Standard validation tools (jsonschema, Pydantic, Great Expectations) operate on individual field values in isolation. Cross-field semantic constraints — "discharge must be after admission", "loan amount must be plausible given income", "diagnosis must be age-appropriate" — are not expressible in JSON Schema and require custom logic.

### 2.2 Why LLMs Make This Worse
LLMs generate date fields from independent distributions unless explicitly constrained. A prompt that says "generate a healthcare intake record" will produce plausible individual values but won't enforce temporal ordering between dates, won't check that a patient's stated age matches their computed age from DOB, and won't verify medication-diagnosis plausibility. These failures are silent — they look correct, pass all automated checks, and enter production.

### 2.3 Four Categories of LLM Semantic Failure
1. **Temporal consistency failures** — dates generated independently; discharge before admission, approval before application
2. **Ratio violations** — numeric fields sampled independently; 52× LTI, impossible employment tenure for age
3. **Categorical inconsistencies** — diagnosis + medication generated without checking clinical plausibility
4. **Silent population drift** — no single record is wrong but the distribution shifts; only detectable at batch level

### 2.4 Domain Rationale
Two regulated domains were chosen because they:
- Have clear, verifiable semantic constraints
- Represent real production use cases (EHR pipelines, loan origination)
- Have different constraint types: temporal + categorical (healthcare) and numeric ratio + temporal (finance)
- Are both subject to regulatory audit requirements (HIPAA, CFPB), making auditability important

---

## 3. SYSTEM ARCHITECTURE

### 3.1 Four-Stage Pipeline
Every record flows through exactly four stages, in sequence:

```
JSON Record
    ↓
[Stage 1] Structural Validation     jsonschema Draft 7
          → valid / error list       types, formats, required fields
    ↓ (FAIL → quarantine immediately, score = 0.0)
[Stage 2] Semantic Validation        10 cross-field rules
          → violations list          temporal, ratio, plausibility
    ↓
[Stage 3] Confidence Scoring         severity-weighted penalties
          → float [0.0, 1.0]         critical: -0.30, warning: -0.12
    ↓
[Stage 4] Decision Router            three tiers
          → trusted / flagged /      ≥0.85 / 0.50–0.84 / <0.50
             quarantined
    ↓
[Output]  Explanation + Audit Log    JSONL per-record trace
```

### 3.2 Rule Engine Design
Rules use a Python decorator pattern:
```python
@register_rule(domain="healthcare_intake", rule_id="HC-003",
               severity="critical", fields=["admission_date","discharge_date"])
def check_discharge_after_admission(record: dict) -> RuleResult:
    passed = discharge >= admission
    return RuleResult(passed=passed, severity="critical",
        message=f"Discharge ({discharge}) precedes admission ({admission})" if not passed else "")
```
The decorator captures metadata (domain, rule ID, severity, affected fields) separately from rule logic. Adding a new domain = adding a new decorated Python file. The pipeline never needs to change.

### 3.3 Confidence Scoring Formula
```
score = 1.0 − (0.30 × critical_violations) − (0.12 × warning_violations)
score = clamp(score, 0.0, 1.0)
```
Thresholds are configurable via environment variables. This preserves severity information that binary pass/fail throws away.

### 3.4 Batch + Drift Path
For batch validation, all records are processed individually, then the aggregated statistics are compared against a stored baseline using four signals:
- **z-score**: normalised shift in numeric field means (threshold: 1.5σ)
- **PSI**: Population Stability Index for categorical distributions (threshold: 0.20)
- **Null-rate delta**: change in per-field null rates (threshold: 15%)
- **Violation-rate delta**: fraction of records violating each rule (threshold: 10%)

Drift detection is orthogonal to per-record routing — a batch of entirely trusted records can still trigger a drift alert.

### 3.5 Module Structure
```
validator/       Pipeline orchestration, structural, semantic, explanation, audit
rules/           Rule registry + healthcare_rules.py + finance_rules.py (10 rules total)
schemas/         JSON Schema Draft 7 definitions for both domains
scoring/         Confidence scorer + decision router
drift/           Baseline profiler + 4-signal drift detector
rag/             FAISS vector store + retriever + RAG explainer + API routes
ingest/          Document upload (PDF/text) → LLM extraction → validation
api/             FastAPI standalone API (original)
backend/         Production FastAPI + SQLite backend
frontend/        Next.js 14 dashboard (6 pages)
analytics/       Usage tracker + structured audit log
observability/   Latency histograms + distributed tracing
resilience/      Circuit breakers with fallbacks (3 per module)
pipeline/        Async processor + FIFO queue with retry + dead-letter
storage/         Thread-safe result store with per-user isolation
auth/            Token-based API authentication
evaluation/      135 test assertions + 12 evaluation charts + metrics CSV
data_gen/        Synthetic dataset generator (600 records)
notebooks/       6 Jupyter notebooks documenting each system component
website/         Self-contained HTML/CSS/JS project webpage (GitHub Pages ready)
docs/report/     Full academic report (PDF + Markdown)
docs/demo/       10-minute video demo script (PDF + Markdown)
```

---

## 4. THE TEN SEMANTIC RULES

### Healthcare Intake (HC-001 to HC-005)
| Rule | Check | Severity | Penalty |
|------|-------|----------|---------|
| HC-001 | `patient_age` matches computed age from DOB + admission_date (±1 yr) | Critical | −0.30 |
| HC-002 | `admission_date ≥ date_of_birth` | Critical | −0.30 |
| HC-003 | `discharge_date ≥ admission_date` | Critical | −0.30 |
| HC-004 | `diagnosis_code` is age-appropriate per ICD-10-CM edit table | Warning | −0.12 |
| HC-005 | `medication` is a plausible treatment for the ICD-10 diagnosis category | Warning | −0.12 |

### Financial Loan Application (FN-001 to FN-005)
| Rule | Check | Severity | Penalty |
|------|-------|----------|---------|
| FN-001 | `approval_date ≥ application_date` (or null) | Critical | −0.30 |
| FN-002 | `loan_amount / annual_income ≤ 10.0` | Critical | −0.30 |
| FN-003 | `existing_debt / annual_income ≤ 0.60` | Warning | −0.12 |
| FN-004 | `employment_length_years ≤ (applicant_age − 16)` | Critical | −0.30 |
| FN-005 | `approved_amount ≤ loan_amount` (or null) | Critical | −0.30 |


---

## 5. PROMPT ENGINEERING COMPONENT

This is central to the course requirement. The project demonstrates four distinct prompt engineering applications.

### 5.1 Synthetic Data Generation Prompts
**Goal:** Generate 600 labeled records (300 per domain) with verifiable semantic properties.

**Three prompt types:**
- **Valid prompts:** state all cross-field constraints affirmatively. "The discharge_date must be on or after the admission_date."
- **Invalid prompts:** flip exactly one constraint while keeping all others active. "Set discharge_date to a date BEFORE admission_date. Example: admission_date = 2024-08-15, discharge_date = 2024-08-08."
- **Edge-case prompts:** target boundary conditions that must pass all rules (same-day discharge, newborn patient, age-18 applicant).

**Triple-fence pattern:**
```
[1] Instruction: "Respond ONLY with a valid JSON object. No markdown, no explanation."
[2] Schema: complete field list with types, constraints, and cross-field rules in plain language
[3] Reinforcement: repeat the JSON-only instruction + a concrete output example
```
Compliance rate (no markdown wrapper, correct types, valid JSON): ~96% on production prompt version. Earlier versions hit 72% (v1) and 88% (v2). The persistent failure mode was the model "correcting" deliberately invalid dates based on its training prior toward coherent data.

**Quality gate:** Every invalid record is verified by the production semantic validator before saving. If the target rule doesn't fire, the record is discarded and regenerated (up to 3 attempts).

**Dataset structure:**
- 120 valid (40%) — 10 demographic profiles cycled
- 120 invalid (40%) — 24 records × 5 rules (exactly one violation each, verified)
- 60 edge-case (20%) — 12 records × 5 boundary types

### 5.2 Dataset Size
The generator is fully scaffolded and tested. Dry-run confirms all 600 records plan correctly. Full generation requires ANTHROPIC_API_KEY and ~15 minutes. Due to API key configuration, the evaluation was run on 16 labeled seed records + 140 audit log records.

### 5.3 Explanation Prompts (Baseline)
Post-validation explanation prompts are structured around the actual validation result:
```
"Given this record: {record_json}.
The following rules were violated: {violations}.
Write a 2-3 sentence explanation of what is wrong and what corrective action is required."
```
Grounded in real validation output, preventing hallucinated explanations. These produce the baseline explanation (avg 42 words, 2.7/6 quality score).

### 5.4 RAG Augmented Explanation Prompts
The augmented prompt template:
```
Domain context + Record JSON + Violation list + Rule messages + 3 retrieved regulatory chunks
→ Instruction to: (1) cite field values, (2) cite retrieved regulation by section,
   (3) explain downstream consequence, (4) give specific remediation step
```
This produces the RAG explanation (avg 175 words, 6.0/6 quality score).

### 5.5 Document Extraction Prompts (New Feature)
Used in the document ingest module. Given raw text from a PDF or text file:
```
"You are a data extraction assistant. Extract ALL of the following fields as a single JSON object.
FIELDS: [15 healthcare fields / 19 finance fields with types and formats]
DOCUMENT: [truncated document text ≤3500 chars]
JSON:"
```

---

## 6. RAG MODULE

### 6.1 Architecture
```
Failed record + violated rules
        ↓
  Query builder (rule IDs + messages + domain hint)
        ↓
  FAISS retriever (top-3 chunks, domain+rule filtered)
        ↓
  Augmented prompt (record + violations + retrieved context)
        ↓
  Claude claude-opus-4-5 (max 800 tokens)
        ↓
  RAGExplanation (baseline text + RAG text + chunks + latency)
```

### 6.2 Knowledge Base
11 synthetic-but-realistic reference documents (~3,000 words total), each citing real regulatory sources:
- CMS Conditions of Participation §482.24(c)
- Joint Commission standard RC.02.01.01
- HL7 FHIR R4 Encounter Resource specification
- CMS Medicare Claims Processing Manual Chapter 1 §30.2
- AHRQ HCUP Coding Guidelines
- ICD-10-CM FY2024 Official Guidelines
- ISMP Annual Report 2023
- Regulation Z (TILA) 12 CFR §1026.2(a)(3)
- CFPB ATR Rule 12 CFR §1026.43
- OCC Comptroller's Handbook — Retail Lending 2023
- SchemaGuard Internal Technical Reference (general LLM failure modes)

### 6.3 Vector Store
- **Chunker:** sentence-aware overlapping chunks, target 400 tokens, 60-token overlap → 17 chunks
- **Embeddings:** all-MiniLM-L6-v2 (384-dim, 22 MB)
- **Index:** FAISS IndexFlatIP (cosine similarity via L2-normalised inner product)
- **Build time:** 8.87 seconds (one-time); loaded via module-level singleton
- **Query time:** <50ms per retrieval

### 6.4 RAG Evaluation Results
6 test cases (3 healthcare + 3 finance), each scored on 6 binary criteria:

| Criterion | Baseline (avg) | RAG (avg) |
|-----------|---------------|-----------|
| Cites rule ID | 6/6 | 6/6 |
| Cites specific field values | 6/6 | 6/6 |
| Has remediation action | 0/6 | **6/6** |
| Cites regulation by name | 0/6 | **6/6** |
| Appropriate length (40–350 words) | 5/6 | 6/6 |
| Explains downstream impact | 0/6 | **6/6** |
| **Composite** | **2.7/6** | **6.0/6** |

Average word count: 42 (baseline) → 175 (RAG). Top retrieval cosine scores: 0.645–0.789. End-to-end latency: 2.8–3.2s per explanation.

### 6.5 API Endpoints
- `POST /rag/explain` — validate + retrieve + generate grounded explanation
- `GET /rag/status` — check if FAISS index is built
- `POST /rag/search` — debug: search knowledge base directly

---

## 7. DOCUMENT INGEST FEATURE

### 7.1 What It Does
A single API call that accepts a PDF or plain-text file upload, uses Claude to extract domain-specific structured fields, then runs the extracted record through the SchemaGuard validation pipeline.

### 7.2 Pipeline
```
Uploaded file (PDF or .txt/.md)
        ↓
  Text extraction (pdfplumber → pypdf fallback, or UTF-8 decode)
        ↓
  LLM field extraction (Claude claude-opus-4-5, domain field list prompt)
        ↓
  SchemaGuard 4-stage validation
        ↓
  IngestResult: {extracted_record, validation, latency_ms}
```

### 7.3 Files
- `ingest/document_ingest.py` — core logic (extract_text + _llm_extract + extract_and_validate)
- `ingest/api_routes.py` — FastAPI router (POST /ingest/upload, GET /ingest/supported-domains)
- `ingest/test_ingest.py` — CLI smoke-test with built-in fixtures

### 7.4 Constraints
- Max file size: 10 MB
- Supported types: .pdf, .txt, .md
- Document text truncated to 3,500 chars for the extraction prompt
- Requires ANTHROPIC_API_KEY

---

## 8. EVALUATION METRICS

### 8.1 Classification Metrics (16 labeled seed records)
| Metric | Healthcare | Finance |
|--------|-----------|---------|
| Precision | 1.0 | 1.0 |
| Recall | 1.0 | 1.0 |
| F1 Score | 1.0 | 1.0 |
| Accuracy | 1.0 | 1.0 |
| False Quarantine Rate | 0% | 0% |

Confusion matrix per domain (8 records): TP=3, FP=0, TN=5, FN=0.

**Note:** Perfect metrics are expected for a deterministic rule-based classifier tested on records specifically designed to target those rules. The meaningful result is the 0% false quarantine rate on all edge cases.

### 8.2 Confidence Distribution (audit log, 140 records)
| Category | Mean confidence |
|----------|----------------|
| Valid/Edge records | 1.000 |
| Invalid (healthcare) | 0.760 |
| Invalid (finance) | 0.700 |
| Gap (HC) | +0.240 |
| Gap (FN) | +0.300 |

Clean bimodal distribution, zero overlap between valid and invalid bands.
Overall: 90 trusted (64%), 50 flagged (36%), 0 quarantined (0%).

### 8.3 Rule Violation Frequency (140 audit-log records, 53 total violations)
Healthcare: HC-003=37, HC-001=3, HC-004=3, HC-002=0, HC-005=0  
Finance: FN-001=6, FN-002=2, FN-004=2, FN-003=0, FN-005=0

HC-003 dominance reflects audit log composition (batch testing focused on temporal errors).

### 8.4 Latency (140 records)
| Percentile | ms |
|-----------|-----|
| p50 | 0.09 |
| p90 | 0.34 |
| p95 | 1.16 |
| p99 | 3.02 |
| max | 7.42 |
| mean | 0.26 |

~3,800 records/second at mean latency. Fully CPU-bound, no I/O. p99 reflects Python warm-up cost.

### 8.5 Tests
- Integration tests: 58/58 passed
- Production tests: 77/77 passed
- Total assertions: 135

### 8.6 Evaluation Plots (12 charts generated)
01_classification_metrics.png — grouped bar, both domains  
02_confusion_matrices.png — heatmaps  
03_confidence_histogram.png — bimodal distribution  
04_confidence_by_category.png — boxplot by valid/invalid/edge  
05_rule_violation_frequency.png — horizontal bar by rule  
06_decision_distribution.png — pie charts  
07_latency_distribution.png — histogram with percentile lines  
08_decisions_over_time.png — stacked area + confidence scatter  
09_drift_signals.png — delta vs threshold ratio bars  
10_confidence_gap.png — separation magnitude  
11_pipeline_throughput.png — records/sec curve  
12_summary_dashboard.png — 6-panel overview


---

## 9. API DESIGN

### 9.1 Standalone API (api/)
Original FastAPI with four routers mounted at the root:

| Router prefix | Tags | Key endpoints |
|--------------|------|---------------|
| `/` | Core | `/validate`, `/batch-validate`, `/health`, `/example` |
| `/async` | Async Pipeline | `/submit`, `/process`, `/result/{id}`, `/status/{id}`, `/jobs`, `/metrics` |
| `/user` | User & Analytics | `/me`, `/stats`, `/jobs`, `/audit` |
| `/rag` | RAG Explanations | `/explain`, `/status`, `/search` |
| `/ingest` | Document Ingest | `/upload`, `/supported-domains` |

### 9.2 Production Backend (backend/)
Separate FastAPI application with SQLite database and `/api/` prefix. Uses four tables:
- `validation_runs` — per-batch metadata
- `record_results` — per-record results with full JSON
- `batch_runs` — batch summary stats
- `rule_violations` — individual rule firings, queryable

Dashboard endpoint (`/api/dashboard`) returns aggregated stats, recent activity feed, and top violated rules for the Next.js frontend.

### 9.3 Async Processing Pattern
```
POST /async/submit → {job_id}   (non-blocking, 202)
POST /async/process              (drains queue, workers)
GET  /async/result/{job_id}      (PENDING / COMPLETED / FAILED)
```
Retry logic: 2 retries → dead-letter queue. Circuit breakers per module. In production, swap in-memory queue for SQS/Kafka, result store for Redis+PostgreSQL.

---

## 10. FRONTEND (Next.js 14)

Six pages:
1. **Dashboard** — live metrics: total validated, trusted %, flagged %, top violated rules, recent activity feed
2. **Validate** — single-record input with domain selector, full result display
3. **Batch** — multi-record upload with aggregate summary + per-record table
4. **Rules** — browsable rule catalog, severity indicators, field descriptions
5. **Audit** — filterable validation history with search and export
6. **Use Cases** — curated example records showing each failure mode

Tech: Next.js 14 App Router, React 18, Tailwind CSS, typed API client (`lib/api.ts`).

---

## 11. RESILIENCE AND OBSERVABILITY

### Circuit Breakers
Three circuit breakers, each independently configured:
- `drift_breaker`: threshold=3 failures, cooldown=30s, fallback=safe empty report
- `semantic_breaker`: threshold=5, cooldown=15s, fallback=empty violations (validation continues)
- `storage_breaker`: threshold=3, cooldown=10s

State machine: CLOSED → OPEN (after threshold failures) → HALF_OPEN (after cooldown) → CLOSED (if probe succeeds).

### Failure Isolation
Every rule executes inside try/except. A crashing rule returns a typed error result; all other rules continue. A failing drift detector returns an empty report; batch results are still returned. The validation result is always returned to the caller even if storage fails.

### Observability
- Latency histograms with p50/p95/p99 per endpoint
- Distributed tracing via request correlation IDs
- Structured logging (JSON) with correlation IDs
- In-memory metrics counters (replaces with Prometheus in production)

---

## 12. SYNTHETIC DATA GENERATION PIPELINE

### Generator
`data_gen/generate_full_dataset.py` — full generator with:
- 10 profile variants per domain for valid records
- Per-rule invalid record generation (24 per rule)
- Edge-case generation (5 types × 12 records)
- Structural quality gate (jsonschema)
- Semantic quality gate (production validator confirms target rule fires)
- Up to 3 retry attempts per rejected record

### Dataset plan (per domain):
- Valid: 120 records, cycling 10 profiles
- Invalid: 120 records (24 × HC-001, 24 × HC-002, 24 × HC-003, 24 × HC-004, 24 × HC-005)
- Edge case: 60 records (newborn, same-day discharge, elderly, minimal fields, emergency same-day)

### Launcher: `./generate_dataset.sh`
- Reads ANTHROPIC_API_KEY from .env
- Installs dependencies if missing
- Supports --dry-run (confirms plan without API calls), --domain hc/fn/both

### Validator: `data_gen/validate_dataset.py`
Post-generation audit: checks every labeled invalid record actually triggers its target rule, flags label mismatches and unexpected violations.

---

## 13. NOTEBOOKS (6 Jupyter notebooks)

| Notebook | Topic | Key content |
|----------|-------|-------------|
| 01_prompt_engineering | Prompt design | Template versions, compliance rates, seed data |
| 02_validation_pipeline | Pipeline walkthrough | 4 stages with live record runs |
| 03_evaluation_metrics | Full evaluation | All 12 charts, tables, analysis |
| 04_drift_detection | Drift monitoring | Baselines, stable vs shifted batches |
| 05_synthetic_data_generation | Dataset pipeline | Generation plan, running instructions |
| 06_rag_explanations | RAG architecture | FAISS demo, baseline vs RAG comparison |

---

## 14. TECH STACK SUMMARY

| Layer | Technology | Notes |
|-------|-----------|-------|
| Core language | Python 3.12 | All backend, rules, scoring, drift |
| API framework | FastAPI + Pydantic v2 | Two separate apps (standalone + production) |
| Frontend | Next.js 14, React 18, Tailwind CSS | 6-page dashboard |
| Database | SQLite (dev) → PostgreSQL (prod) | 4 tables |
| Schema validation | jsonschema Draft 7 | Stage 1 structural check |
| LLM | Claude claude-opus-4-5 (Anthropic) | Data generation, RAG explanations, doc extraction |
| Vector store | FAISS IndexFlatIP | 384-dim, cosine similarity |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | 22 MB model, 384-dim |
| PDF extraction | pdfplumber → pypdf fallback | Document ingest |
| UI (legacy) | Streamlit | Demo/fallback |
| Tests | pytest | 135 assertions across integration + production |
| Evaluation | matplotlib, numpy | 12 charts, JSON + CSV reports |
| Auth | Token-based (header) | Demo key: sg-key-demo-000 |

---

## 15. DESIGN DECISIONS AND TRADEOFFS

### Deterministic Rules vs. LLM Classifier
**Chosen:** deterministic Python functions. Same input → same output. Full audit trail. No inference cost per record.  
**Tradeoff:** rules only catch what was explicitly coded. An LLM classifier could catch novel patterns.  
**Rationale:** for regulated industries (healthcare, finance), auditability is non-negotiable. An LLM classifier that produces different results on identical inputs is legally problematic.

### Continuous Confidence Score vs. Binary Pass/Fail
**Chosen:** continuous 0–1 score with three routing tiers.  
**Rationale:** preserves severity information. A record with one warning-level violation is different from a record with two critical violations. Downstream systems can handle each tier differently.

### Sync + Async, Both Available
**Chosen:** `/validate` (sync, <1ms), `/async/submit → /async/process → /async/result` (async with queue).  
**Rationale:** sync for real-time single-record use; async for batch ETL pipelines. Client chooses.

### In-Memory Queue + Store
**Chosen:** in-memory deque and dict for zero-dependency setup.  
**Production path:** Queue → Kafka/SQS; Store → Redis + PostgreSQL. Interfaces are clean — one import change each.

### Drift Detection as Supplementary Signal
**Chosen:** drift detection runs after per-record processing and doesn't block results.  
**Rationale:** drift is statistical and inherently approximate. A batch can be trusted per-record and still show drift. Blocking on drift would be too aggressive.

---

## 16. KNOWN LIMITATIONS

1. **Small evaluation dataset.** 16 labeled seed records is sufficient to confirm correct rule implementation but too small for statistical generalization. 95% CI for precision on 3 invalid records ≈ [0.29, 1.0].

2. **Small drift baselines.** Baselines profiled from 3 records each. Produces unreliable variance estimates for z-score drift detection. Production requires 100–500 records.

3. **Synthetic evaluation circularity.** Rules were designed knowing what the test data would look like. An adversarial evaluation on real EHR or loan application data would be more honest.

4. **HC-003 dataset imbalance.** HC-003 (discharge before admission) represents 37/40 healthcare violations in the audit log because it was the primary test case in the async batch evaluation. This doesn't reflect the real-world frequency distribution.

5. **Independent violation penalty.** The confidence formula treats violations independently. Two violations sharing a common cause (transposed year causing both HC-001 and HC-003) get double-penalized. An interaction-aware scorer is deferred.

6. **No demographic fairness audit.** HC-004 is age-differential by design. A production deployment would require verifying that quarantine rates are not systematically higher for records representing protected demographic groups.

7. **API key dependency.** Features requiring LLM calls (RAG explanations, document ingest, synthetic data generation) require ANTHROPIC_API_KEY. Validation pipeline and drift detection work without it.

---

## 17. FUTURE WORK (Prioritized)

| Priority | Item |
|----------|------|
| High | Generate full 600-record dataset (scaffolded, needs API key + 15 min) |
| High | Profile drift baselines from 100+ records |
| Medium | Add 2–3 new domains (insurance claims, e-prescriptions) |
| Medium | Active learning loop: reviewer corrections on flagged records recalibrate thresholds |
| Medium | LLM-assisted rule discovery: mine audit-log patterns to propose new rules |
| Low | Real-time streaming validation via WebSocket |
| Low | Multi-model RAG evaluation: Claude vs GPT-4o vs Gemini |
| Low | Interaction-aware confidence scoring (violation dependency graph) |

---

## 18. FILE COUNT AND SCOPE

```
Python files:       ~45 .py files across 15 packages
Jupyter notebooks:  6
Evaluation charts:  13 (12 metrics + 1 RAG comparison)
Documentation:      30+ markdown files + 2 PDFs (report + demo script)
Tests:              135 assertions (58 integration + 77 production)
Website:            1,603-line self-contained HTML/CSS/JS (GitHub Pages ready)
Project report:     Full academic PDF (467 KB, 10 sections)
Demo script:        Full 10-minute video script (PDF + Markdown)
```

---

## 19. SUGGESTED REVIEW QUESTIONS FOR CHATGPT

The following questions would be useful to get specific feedback on:

1. **Is the 1.0 F1 score meaningful given the dataset is both small and designed to target specific rules?** How would you suggest framing this result more honestly in a course submission?

2. **The confidence scoring formula is purely additive (no interaction effects between violations). Is there a simple extension that would handle the case where multiple violations share a common cause?**

3. **The RAG knowledge base uses synthetic documents with real citations. What are the risks of this approach compared to using real regulatory text?**

4. **The project has two separate FastAPI applications (api/ for standalone, backend/ for production). Is this a reasonable architectural decision for a course project, or does it add confusing complexity?**

5. **For the drift detection baselines profiled from 3 records each — what is the minimum sample size that would produce reliable PSI and z-score estimates?**

6. **The document ingest feature truncates text to 3,500 characters. What extraction quality issues would this cause for longer clinical documents?**

7. **The rules are deterministic Python functions, which is correct for auditability. But what types of semantic failures would these rules completely miss?**

8. **What would a meaningful adversarial evaluation look like for this system?**

---

*End of summary. Total length: ~2,800 words. Intended for submission to ChatGPT for a detailed technical review.*

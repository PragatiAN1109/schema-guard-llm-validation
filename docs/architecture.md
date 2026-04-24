# Architecture — SchemaGuard

## System Flow

```
                         ┌─────────────────┐
                         │   LLM Output    │
                         │    (JSON)       │
                         └────────┬────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │     STRUCTURAL VALIDATION   │
                    │  JSON Schema Draft 7 check  │
                    │  types, formats, required   │
                    └─────────────┬──────────────┘
                            PASS? │ FAIL → quarantine
                                  │
                    ┌─────────────▼──────────────┐
                    │     SEMANTIC VALIDATION     │
                    │  10 cross-field rules       │
                    │  temporal, ratio, plausible │
                    └─────────────┬──────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │     CONFIDENCE SCORING      │
                    │  severity-weighted 0.0–1.0  │
                    │  configurable penalties     │
                    └─────────────┬──────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │     DECISION ROUTING        │
                    └──┬──────────┬──────────┬───┘
                       │          │          │
                  🟢 TRUSTED  🟡 FLAGGED  🔴 QUARANTINED
                    ≥ 0.85    0.50–0.84     < 0.50
                       │          │          │
                       └──────────┼──────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │  EXPLANATION + AUDIT LOG    │
                    └────────────────────────────┘
```

## Batch + Drift Path

```
  Batch of N records
       │
       ▼
  Per-record pipeline (above) × N
       │
       ▼
  Aggregate: T/F/Q counts, mean confidence
       │
       ▼
  ┌─────────────────────────────────┐
  │       DRIFT DETECTION           │
  │  Compare vs stored baseline     │
  │                                 │
  │  Numeric:      z-score shift    │
  │  Categorical:  PSI              │
  │  Null rates:   absolute delta   │
  │  Violations:   rate change      │
  └──────────────┬──────────────────┘
                 │
           Threshold exceeded?
           │              │
        ⚠ ALERT       ✅ STABLE
```

## Component Map

```
  data_gen/        Prompt templates + seed datasets
       │
       ▼
  schemas/         JSON Schema Draft 7 definitions
       │
       ├───────────────────────┐
       ▼                       ▼
  validator/               rules/
  structural.py            rule_registry.py
  semantic.py              healthcare_rules.py (5)
  pipeline.py              finance_rules.py (5)
  batch_validation.py
  explanation.py
  audit.py
       │
       ├──────────┐
       ▼          ▼
  scoring/     drift/
  confidence   baseline
  decision     detector
       │          │
       ▼          ▼
  ┌────────┐  ┌──────────┐
  │  api/  │  │   ui/    │
  │ FastAPI│  │Streamlit │
  └────────┘  └──────────┘
       │          │
       ▼          ▼
  evaluation/
  metrics, charts, integration tests
```

## Module Responsibilities

| Module | Files | Responsibility |
|--------|-------|---------------|
| `schemas/` | 2 JSON files | Domain schema definitions |
| `rules/` | registry + 2 rule files | 10 semantic rules with severity |
| `validator/` | 7 Python files | Pipeline orchestration, batch, explanation, audit |
| `drift/` | baseline + detector | 4-signal drift monitoring |
| `scoring/` | confidence + decision | Weighted scoring + three-tier routing |
| `config.py` | 1 file | Centralized thresholds (env-overridable) |
| `utils/` | errors + logger | Typed exceptions + structured logging |
| `api/` | main + routes + models | REST endpoints with Swagger |
| `ui/` | app.py | Streamlit demo (3 tabs) |
| `evaluation/` | 6 Python files | Metrics, charts, integration tests |

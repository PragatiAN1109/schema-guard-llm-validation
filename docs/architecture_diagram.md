# Architecture Diagram

## End-to-End System Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                        SINGLE RECORD FLOW                        │
└──────────────────────────────────────────────────────────────────┘

  ┌─────────┐     ┌───────────────┐     ┌───────────────┐
  │  Input   │────▶│   schemas/    │────▶│    rules/     │
  │  JSON    │     │  Structural   │     │   Semantic    │
  │  Record  │     │  Validation   │     │   Validation  │
  └─────────┘     └───────┬───────┘     └───────┬───────┘
                          │                     │
                    FAIL? ▼ stop          FAIL? ▼ continue
                          │                     │
                          └──────────┬──────────┘
                                     │
                                     ▼
                          ┌───────────────────┐
                          │     scoring/      │
                          │  Confidence Score  │
                          │    (0.0 – 1.0)    │
                          └─────────┬─────────┘
                                    │
                                    ▼
                          ┌───────────────────┐
                          │     scoring/      │
                          │  Decision Router   │
                          └─────────┬─────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              ┌──────────┐   ┌──────────┐   ┌──────────────┐
              │ 🟢 TRUSTED│   │ 🟡 FLAGGED│   │🔴 QUARANTINED│
              │  ≥ 0.85  │   │ 0.50–0.84│   │   < 0.50    │
              └──────────┘   └──────────┘   └──────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │  validator/explanation.py  │
                    │  Human-readable summary    │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │    validator/audit.py      │
                    │    JSONL audit log entry   │
                    └───────────────────────────┘


┌──────────────────────────────────────────────────────────────────┐
│                        BATCH + DRIFT FLOW                        │
└──────────────────────────────────────────────────────────────────┘

  ┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
  │  Batch of    │────▶│  Per-record      │────▶│  Aggregate       │
  │  N records   │     │  pipeline        │     │  batch stats     │
  └──────────────┘     │  (loop above)    │     │  T / F / Q counts│
                       └─────────────────┘     └────────┬─────────┘
                                                         │
                                                         ▼
                                              ┌─────────────────────┐
                                              │   drift/            │
                                              │   drift_detector.py │
                                              └────────┬────────────┘
                                                       │
                                  ┌────────────────────┼────────────────────┐
                                  ▼                    ▼                    ▼
                          ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
                          │ Numeric      │   │ Categorical  │   │ Null-rate &  │
                          │ z-score      │   │ PSI          │   │ Violation    │
                          │ shift        │   │ shift        │   │ rate shift   │
                          └──────────────┘   └──────────────┘   └──────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │  Drift Alerts    │
                                              │  (if threshold   │
                                              │   exceeded)      │
                                              └─────────────────┘


┌──────────────────────────────────────────────────────────────────┐
│                       MODULE RESPONSIBILITIES                     │
└──────────────────────────────────────────────────────────────────┘

  ┌─────────────┐
  │  data_gen/  │  Prompt templates, seed data, generation scripts
  └──────┬──────┘
         │ generates
         ▼
  ┌─────────────┐
  │  schemas/   │  JSON Schema definitions (healthcare, finance)
  └──────┬──────┘
         │ used by
         ▼
  ┌─────────────┐     ┌─────────────┐
  │ validator/  │────▶│  scoring/   │  Confidence + routing
  │  structural │     └─────────────┘
  │  semantic   │
  │  pipeline   │────▶┌─────────────┐
  │  batch      │     │   drift/    │  Baseline + detection
  │  explanation│     └─────────────┘
  │  audit      │
  └──────┬──────┘
         │ exposed via
         ▼
  ┌─────────────┐     ┌─────────────┐
  │    api/     │     │    ui/      │
  │  FastAPI    │     │  Streamlit  │
  │  REST       │     │  Demo       │
  └─────────────┘     └─────────────┘
         │                   │
         └─────────┬─────────┘
                   ▼
            ┌─────────────┐
            │ evaluation/ │  Metrics, charts, test runners
            └─────────────┘
```

## Confidence Scoring Breakdown

```
  Base Score: 1.0
    │
    ├── Structural failure?     → 0.0 (immediate)
    │
    ├── Critical violation?     → -0.30 per violation
    ├── Warning violation?      → -0.12 per violation
    ├── Info violation?         → -0.05 per violation
    │
    ├── Drift alert? (batch)    → -0.03 per alert (max -0.15)
    ├── No rules evaluated?     → -0.05
    │
    └── Final: clamp [0.0, 1.0]
```

## Decision Routing Logic

```
  confidence ≥ 0.85  AND  all checks pass       → TRUSTED
  confidence ≥ 0.85  AND  non-critical warnings  → FLAGGED
  0.50 ≤ confidence < 0.85                       → FLAGGED
  critical violation  AND  conf < 0.85           → QUARANTINED
  confidence < 0.50                              → QUARANTINED
  structural failure                             → QUARANTINED
```

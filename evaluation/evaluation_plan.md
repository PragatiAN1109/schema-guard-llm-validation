# Evaluation Plan

## Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| **Structural accuracy** | % of records where schema validation result matches the label | 100% (deterministic) |
| **Semantic precision** | Of records flagged as invalid, % that are actually invalid | ≥ 0.90 |
| **Semantic recall** | Of actually invalid records, % that are flagged | ≥ 0.85 |
| **False quarantine rate** | % of valid records incorrectly routed to quarantined | < 5% |
| **Drift detection rate** | % of simulated distribution shifts correctly detected | ≥ 90% |
| **Drift false alarm rate** | % of stable batches that trigger a drift alert | < 10% |
| **Confidence separation** | IQR gap between valid and invalid record scores | Non-overlapping |

## Dataset Usage

| Dataset | Used For |
|---------|----------|
| `data_gen/datasets/labeled/healthcare_*.jsonl` | Healthcare validation evaluation |
| `data_gen/datasets/labeled/finance_*.jsonl` | Finance validation evaluation |
| Synthetic shifted batches (generated at eval time) | Drift detection evaluation |

## Evaluation Process

1. Load labeled dataset for a domain
2. Run each record through the full validation pipeline (`validator/pipeline.py`)
3. Compare pipeline output to ground-truth labels
4. Compute metrics per domain
5. Generate confusion matrix, precision/recall chart, confidence distribution chart
6. Save results to `evaluation/results/`

## Result Storage

```
evaluation/
├── results/
│   ├── healthcare_metrics.json
│   ├── finance_metrics.json
│   ├── healthcare_confusion.png
│   ├── finance_confusion.png
│   ├── confidence_distribution.png
│   └── drift_detection_results.json
├── evaluate.py
├── metrics.py
└── evaluation_plan.md
```

## Drift Evaluation

Drift detection is evaluated separately:

1. Build baseline profile from the labeled valid records
2. Generate a shifted batch (modify distribution of 2–3 fields)
3. Run drift check against baseline
4. Verify alerts are raised for shifted fields and not raised for stable fields
5. Repeat with multiple shift magnitudes to test sensitivity

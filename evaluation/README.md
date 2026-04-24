# evaluation/

Evaluation scripts, metrics, charts, and test suites for SchemaGuard.

## Running

```bash
# Full evaluation (validation + drift + charts + summary)
python -m evaluation.run_full_evaluation

# Validation-only test
python -m evaluation.test_validation

# Drift and scoring test
python -m evaluation.test_drift_and_scoring

# Basic evaluation
python -m evaluation.evaluate
```

## Files

| File | Purpose |
|------|---------|
| `run_full_evaluation.py` | Complete evaluation pipeline: accuracy, drift, charts, summary |
| `evaluate.py` | Core evaluation runner against labeled seed data |
| `test_validation.py` | Per-record validation test with printed output |
| `test_drift_and_scoring.py` | Drift detection and scoring test with simulated shifts |
| `metrics.py` | Precision, recall, F1, false-quarantine rate, confidence separation |
| `charts.py` | Generates HTML chart files (confidence, metrics table, decisions) |

## Output

Results are saved to `evaluation/results/`:

| File | Description |
|------|-------------|
| `healthcare_eval_results.json` | Per-record results + metrics for healthcare |
| `finance_eval_results.json` | Per-record results + metrics for finance |
| `evaluation_summary.json` | Combined summary across both domains |
| `confidence_separation.html` | Bar chart: valid vs invalid confidence scores |
| `metrics_table.html` | Side-by-side metrics comparison table |
| `decision_distribution.html` | Stacked bar: trusted/flagged/quarantined per domain |

## Metrics

| Metric | Description |
|--------|-------------|
| Precision | % of flagged records that are actually invalid |
| Recall | % of invalid records correctly caught |
| F1 Score | Harmonic mean of precision and recall |
| Accuracy | Overall correct classification rate |
| False Quarantine Rate | % of valid records incorrectly quarantined |
| Confidence Separation | Mean confidence gap between valid and invalid |

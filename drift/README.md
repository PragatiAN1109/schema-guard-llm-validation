# drift/

Distribution drift detection module for SchemaGuard.

## Files

| File | Purpose |
|------|---------|
| `drift_detector.py` | High-level drift detection. Combines numeric shift (z-score), categorical shift (PSI), null-rate tracking, and violation frequency monitoring into a unified drift report. |
| `baseline.py` | Builds and stores statistical baseline profiles. Tracks mean, std, percentiles for numeric fields and frequency distributions for categorical fields. |
| `detector.py` | Low-level detection primitives. Normalized mean shift for numeric fields, PSI for categorical fields. |
| `baselines/` | Stored baseline JSON profiles per domain (generated at runtime). |

## Usage

```python
from drift.drift_detector import generate_baseline, run_drift_detection

# Generate baseline from reference valid records
profile = generate_baseline(valid_records, "healthcare_intake")

# Detect drift in a new batch
report = run_drift_detection(new_batch, "healthcare_intake", validation_results=batch_results)
# report["drift_detected"] -> bool
# report["alerts"] -> list of drift alerts with severity
# report["drift_metrics"] -> per-field metrics
```

## What Gets Tracked

| Signal | Metric | Threshold |
|--------|--------|-----------|
| Numeric field shift | z-score of mean difference | > 1.5 |
| Categorical distribution shift | Population Stability Index (PSI) | > 0.20 |
| Null rate change | Absolute difference | > 0.15 |
| Violation frequency change | Absolute difference | > 0.10 |

## Output Format

```json
{
  "drift_detected": true,
  "checked_fields": 6,
  "drift_metrics": {
    "patient_age": {"type": "numeric", "z_shift": 2.8, "alert": true, ...},
    "gender": {"type": "categorical", "psi": 0.45, "alert": true, ...}
  },
  "alerts": [
    {"field": "patient_age", "type": "numeric_shift", "severity": "medium", "message": "..."}
  ]
}
```

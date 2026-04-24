# System Outputs

What SchemaGuard returns for every validated record.

## Per-Record Response

| Field | Type | Description |
|-------|------|-------------|
| `record_id` | string | Unique record identifier |
| `domain` | string | `healthcare_intake` or `financial_loan_application` |
| `structural_valid` | boolean | Whether the record passes JSON schema validation |
| `structural_errors` | list | Field-level schema violations (field, expected, actual) |
| `semantic_valid` | boolean | Whether the record passes all cross-field rules |
| `violated_rules` | list | Each entry: rule_id, rule_name, severity, fields_involved, message |
| `explanation` | string | Human-readable summary of what failed and why |
| `confidence_score` | float | 0.0–1.0 composite quality score |
| `decision` | string | `trusted`, `flagged`, or `quarantined` |
| `audit_log` | object | Timestamp, domain, results summary, rules evaluated, processing time |

## Batch Response (additional)

| Field | Type | Description |
|-------|------|-------------|
| `total_records` | int | Records in batch |
| `trusted_count` | int | Routed to trusted |
| `flagged_count` | int | Routed to flagged |
| `quarantined_count` | int | Routed to quarantined |
| `mean_confidence` | float | Average confidence across batch |
| `drift_alert` | object | Drift detected (bool), affected fields, metric scores, thresholds |

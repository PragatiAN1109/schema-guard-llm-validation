# validator/

Core validation pipeline for SchemaGuard.

## Files

| File | Purpose |
|------|---------|
| `schema_validator.py` | High-level schema validation interface. Handles JSON string input, non-dict input, unknown domains. Returns `structural_valid` + `errors` + `error_count`. |
| `structural.py` | Low-level JSON schema validation using jsonschema Draft7Validator. Loads schemas from `schemas/`, caches them, returns field-level error details. |
| `semantic.py` | Runs all registered domain rules from `rules/` against a record. Returns violations list and full rule results. |
| `pipeline.py` | Orchestrates the full flow: structural → semantic → confidence → routing → explanation → audit. Main entry point: `validate_record()`. |
| `explanation.py` | Converts validation results into human-readable explanations. Handles structural errors, semantic violations (by severity), and combined summaries. |
| `audit.py` | Creates JSONL audit log entries per validation run (timestamp, results, rules, processing time). |

## Usage

```python
# Full pipeline (recommended)
from validator import validate_record
result = validate_record(record_dict, "healthcare_intake")

# Schema-only check with error handling
from validator import validate_schema
result = validate_schema(json_string_or_dict, "financial_loan_application")

# Standalone explanation
from validator import build_explanation
text = build_explanation(structural_result, semantic_result, "quarantined", "HC-001")
```

## Pipeline Flow

```
Input (record + domain)
  → schema_validator / structural.py (schema check)
  → semantic.py (cross-field rules)
  → scoring/confidence.py (0–1 score)
  → scoring/router.py (trusted / flagged / quarantined)
  → explanation.py (human-readable summary)
  → audit.py (JSONL log)
  → return full result
```

## Output Format

```json
{
  "record_id": "HC-val-a8f3c1",
  "domain": "healthcare_intake",
  "structural_valid": true,
  "structural_errors": [],
  "semantic_valid": false,
  "violated_rules": [ ... ],
  "all_rule_results": [ ... ],
  "explanation": "Record HC-val-a8f3c1: Record failed validation. Critical issues: ...",
  "confidence_score": 0.70,
  "decision": "flagged",
  "audit_entry": { ... }
}
```

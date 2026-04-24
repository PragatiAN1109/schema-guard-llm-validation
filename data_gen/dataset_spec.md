# Dataset Specification

## Record Categories

| Category | Description | Schema Valid | Semantic Valid |
|----------|-------------|-------------|----------------|
| **valid** | Correct structure and logic | yes | yes |
| **invalid** | Correct structure, semantic contradiction | yes | no |
| **edge_case** | Correct structure, boundary values, no violations | yes | yes |

## Target Size Per Domain

| Domain | Valid (60%) | Invalid (25%) | Edge Case (15%) | Total |
|--------|------------|---------------|-----------------|-------|
| Healthcare intake | 180 | 75 | 45 | 300 |
| Financial loan | 180 | 75 | 45 | 300 |
| **Combined** | 360 | 150 | 90 | **600** |

## Invalid Record Distribution

Invalid records are spread across rule violations:

**Healthcare (75 invalid):**
| Rule | Count | Violation |
|------|-------|-----------|
| HC-001 | 15 | Age mismatch |
| HC-002 | 15 | Diagnosis before birth |
| HC-003 | 15 | Discharge before admission |
| HC-004 | 15 | Age-inappropriate diagnosis |
| HC-005 | 15 | Implausible medication |

**Finance (75 invalid):**
| Rule | Count | Violation |
|------|-------|-----------|
| FN-001 | 15 | Approval before application |
| FN-002 | 15 | Extreme loan-to-income |
| FN-003 | 15 | Impossible DTI ratio |
| FN-004 | 15 | Employment length vs age |
| FN-005 | 15 | Approved > requested |

Each group of 15 includes 5 easy, 5 medium, and 5 hard difficulty records.

## Output Format

Each record is stored as a single JSON object per line (JSONL format).

```json
{
  "record_id": "HC-gen-0042",
  "domain": "healthcare_intake",
  "category": "invalid",
  "prompt_type": "healthcare_invalid_HC003_medium",
  "llm_output_json": {
    "patient_id": "P-2847",
    "first_name": "Maria",
    "..."
  },
  "structural_valid": true,
  "semantic_valid": false,
  "violated_rules": ["HC-003"],
  "difficulty": "medium",
  "notes": "Discharge 5 days before admission"
}
```

## Label Fields

| Field | Type | Description |
|-------|------|-------------|
| `record_id` | string | Unique ID: `{domain_prefix}-gen-{number}` |
| `domain` | string | `healthcare_intake` or `financial_loan_application` |
| `category` | string | `valid`, `invalid`, or `edge_case` |
| `prompt_type` | string | Identifier for the prompt template + variant used |
| `llm_output_json` | object | The raw generated record |
| `structural_valid` | boolean | Whether the record passes schema validation |
| `semantic_valid` | boolean | Whether the record passes all semantic rules |
| `violated_rules` | list[string] | Rule IDs intentionally violated (empty for valid/edge) |
| `difficulty` | string | `easy`, `medium`, `hard`, or `n/a` |
| `notes` | string | Brief description of the violation or edge condition |

## File Layout

```
data_gen/datasets/
├── raw/
│   ├── healthcare_raw.jsonl
│   └── finance_raw.jsonl
├── labeled/
│   ├── healthcare_labeled.jsonl
│   └── finance_labeled.jsonl
```

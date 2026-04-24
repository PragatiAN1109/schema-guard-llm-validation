# API Contract

Base URL: `http://localhost:8000`

All request and response bodies are JSON.

---

## POST /validate

Validate a single record.

**Request:**
```json
{
  "domain": "healthcare_intake",
  "record": {
    "patient_id": "P-1042",
    "first_name": "Maria",
    "last_name": "Santos",
    "date_of_birth": "1985-03-14",
    "gender": "female",
    "admission_date": "2024-06-10",
    "discharge_date": "2024-06-03",
    "diagnosis_code": "J18.9",
    "diagnosis_description": "Pneumonia, unspecified organism",
    "treating_physician": "Dr. Alan Reed",
    "medication": "Amoxicillin",
    "insurance_provider": "BlueCross"
  }
}
```

**Response:**
```json
{
  "record_id": "val_a8f3c1",
  "domain": "healthcare_intake",
  "structural_valid": true,
  "structural_errors": [],
  "semantic_valid": false,
  "violated_rules": [
    {
      "rule_id": "HC-003",
      "rule_name": "discharge_after_admission",
      "severity": "critical",
      "fields": ["admission_date", "discharge_date"],
      "message": "Discharge date (2024-06-03) precedes admission date (2024-06-10)"
    }
  ],
  "explanation": "Record is structurally valid but contains a critical temporal contradiction: discharge occurred before admission.",
  "confidence_score": 0.15,
  "decision": "quarantined",
  "audit_entry": {
    "timestamp": "2026-04-03T14:22:08Z",
    "rules_evaluated": ["HC-001", "HC-002", "HC-003", "HC-004", "HC-005"],
    "rules_violated": ["HC-003"],
    "processing_time_ms": 42
  }
}
```

---

## POST /batch-validate

Validate multiple records in one request.

**Request:**
```json
{
  "domain": "financial_loan_application",
  "records": [
    { "applicant_name": "John Doe", "annual_income": 55000, "loan_amount": 120000, "..." : "..." },
    { "applicant_name": "Jane Roe", "annual_income": 72000, "loan_amount": 3800000, "..." : "..." }
  ]
}
```

**Response:**
```json
{
  "batch_id": "batch_9d1e4a",
  "domain": "financial_loan_application",
  "total_records": 2,
  "results": [
    {
      "record_id": "val_001",
      "structural_valid": true,
      "semantic_valid": true,
      "confidence_score": 0.92,
      "decision": "trusted"
    },
    {
      "record_id": "val_002",
      "structural_valid": true,
      "semantic_valid": false,
      "violated_rules": [
        {
          "rule_id": "FN-002",
          "rule_name": "loan_to_income_ratio",
          "severity": "critical",
          "fields": ["annual_income", "loan_amount"],
          "message": "Loan amount ($3,800,000) is 52.8x annual income ($72,000), exceeds 10x limit"
        }
      ],
      "confidence_score": 0.08,
      "decision": "quarantined"
    }
  ],
  "summary": {
    "trusted": 1,
    "flagged": 0,
    "quarantined": 1,
    "mean_confidence": 0.50
  }
}
```

---

## POST /generate

Generate synthetic records using the data generation pipeline.

**Request:**
```json
{
  "domain": "healthcare_intake",
  "count": 10,
  "type": "mixed",
  "split": {
    "valid": 0.6,
    "invalid": 0.25,
    "edge_case": 0.15
  }
}
```

**Response:**
```json
{
  "domain": "healthcare_intake",
  "generated": 10,
  "records": [
    {
      "record": { "patient_id": "P-gen-001", "..." : "..." },
      "label": {
        "structural_valid": true,
        "semantic_valid": false,
        "violated_rules": ["HC-003"],
        "prompt_type": "invalid",
        "difficulty": "medium"
      }
    }
  ]
}
```

---

## GET /drift-check

Run drift detection against the current baseline.

**Request:** Query parameters
- `domain` (required): `healthcare_intake` or `financial_loan_application`
- `batch_id` (optional): specific batch to check

**Response:**
```json
{
  "domain": "healthcare_intake",
  "drift_detected": true,
  "checked_fields": 8,
  "alerts": [
    {
      "field": "patient_age",
      "metric": "psi",
      "baseline_mean": 45.2,
      "current_mean": 31.8,
      "drift_score": 0.34,
      "threshold": 0.20,
      "alert": true
    }
  ],
  "stable_fields": ["gender", "insurance_provider", "diagnosis_code"]
}
```

---

## GET /metrics

Retrieve evaluation metrics from the last evaluation run.

**Response:**
```json
{
  "domain": "healthcare_intake",
  "dataset_size": 300,
  "structural_accuracy": 1.0,
  "semantic_precision": 0.93,
  "semantic_recall": 0.87,
  "false_quarantine_rate": 0.04,
  "mean_confidence_valid": 0.91,
  "mean_confidence_invalid": 0.22,
  "last_evaluated": "2026-04-03T14:30:00Z"
}
```

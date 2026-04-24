# Before vs. After — SchemaGuard Examples

---

## Example 1: Discharge Before Admission

### Before (Raw LLM Output)

```json
{
  "patient_id": "P-4412",
  "first_name": "Sarah",
  "last_name": "Mitchell",
  "date_of_birth": "1990-01-20",
  "gender": "female",
  "admission_date": "2024-08-15",
  "discharge_date": "2024-08-08",
  "diagnosis_code": "N39.0",
  "diagnosis_description": "Urinary tract infection",
  "treating_physician": "Dr. Mark Evans",
  "medication": "Ciprofloxacin",
  "patient_age": 34,
  "emergency_admission": false
}
```

**JSON Schema says:** ✅ Valid — all fields present, correct types, valid date formats.

**Reality:** Patient was discharged **7 days before** being admitted. Impossible.

### After SchemaGuard

```
Structural:  ✅ PASS
Semantic:    ❌ FAIL
  Rule HC-003: Discharge (2024-08-08) precedes admission (2024-08-15)
Confidence:  0.70
Decision:    🔴 QUARANTINED

Explanation: Record failed validation. Critical: discharge_after_admission —
Discharge date (2024-08-08) precedes admission date (2024-08-15).
This record has been quarantined and should not be used downstream.
```

---

## Example 2: Loan 52x Annual Income

### Before (Raw LLM Output)

```json
{
  "application_id": "LA-33190",
  "applicant_name": "Jessica Williams",
  "annual_income": 48000,
  "loan_amount": 2500000,
  "loan_purpose": "home_purchase",
  "credit_score": 680,
  "existing_debt": 15000
}
```

**JSON Schema says:** ✅ Valid — loan_amount is an integer, all fields present.

**Reality:** $2.5M loan on $48K income = **52x ratio**. No lender would approve this.

### After SchemaGuard

```
Structural:  ✅ PASS
Semantic:    ❌ FAIL
  Rule FN-002: Loan $2,500,000 is 52.1x income $48,000 (limit: 10x)
Confidence:  0.70
Decision:    🔴 QUARANTINED
```

---

## Example 3: Child With Adult Diagnosis

### Before (Raw LLM Output)

```json
{
  "patient_id": "P-1187",
  "first_name": "Lily",
  "last_name": "Thompson",
  "date_of_birth": "2019-02-14",
  "diagnosis_code": "M81.0",
  "diagnosis_description": "Age-related osteoporosis",
  "patient_age": 5
}
```

**JSON Schema says:** ✅ Valid — M81.0 is a real ICD-10 code.

**Reality:** Osteoporosis is an **age-related** condition. A 5-year-old cannot have it.

### After SchemaGuard

```
Structural:  ✅ PASS
Semantic:    ❌ FAIL
  Rule HC-004 [warning]: Diagnosis M81.0 is adult-only, patient age is 5
Confidence:  0.88
Decision:    🟡 FLAGGED

(Warning-severity: flagged for review, not quarantined)
```

---

## Example 4: Valid Record — Clean Pass

### Before (Raw LLM Output)

```json
{
  "patient_id": "P-3021",
  "first_name": "James",
  "last_name": "Carter",
  "date_of_birth": "1978-11-02",
  "admission_date": "2024-09-14",
  "discharge_date": "2024-09-19",
  "diagnosis_code": "J18.9",
  "diagnosis_description": "Pneumonia, unspecified organism",
  "medication": "Azithromycin",
  "patient_age": 45
}
```

**JSON Schema says:** ✅ Valid.

**SchemaGuard says:** ✅ Also valid — and here's why.

### After SchemaGuard

```
Structural:  ✅ PASS
Semantic:    ✅ PASS (5/5 rules evaluated, all passed)
Confidence:  1.00
Decision:    🟢 TRUSTED

Explanation: Passed all validation checks. No issues found.
```

---

## Example 5: Batch Drift Detection

### Before (Week 1 → Week 4)

Week 1: LLM generates patients aged 25–82, balanced gender distribution.
Week 4: LLM generates patients aged 18–35, 90% female.

**No individual record is wrong.** Every record passes schema *and* semantic validation.

### After SchemaGuard (Drift Alert)

```
⚠ DRIFT DETECTED — 2 alerts

  [HIGH] patient_age: mean shifted 3.2 std devs (48.3 → 27.1)
  [HIGH] gender: PSI = 1.84 (threshold: 0.20)

Recommendation: Investigate LLM prompt or model changes.
Output quality may be degrading.
```

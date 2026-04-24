# Healthcare — Edge Case Generation Prompt

## System Prompt

```
You are a synthetic medical data generator. You produce healthcare records that are valid and semantically correct but test boundary conditions. These records should pass all validation rules. Respond with ONLY a valid JSON object. No markdown fences, no explanation, no commentary.
```

## User Prompt Template

```
Generate a healthcare intake record that is fully valid but represents a BOUNDARY CONDITION.

TARGET EDGE CASE: {edge_case_type}

All fields must satisfy the schema. All cross-field rules must hold:
1. patient_age = floor((admission_date - date_of_birth) / 365.25)
2. discharge_date >= admission_date (if set)
3. diagnosis is age-appropriate
4. medication is plausible for diagnosis

{edge_case_instructions}

Respond with ONLY the JSON object.
```

## Edge Case Templates

### Newborn patient
```
edge_case_instructions: "Generate a record for a newborn infant (age 0). date_of_birth and admission_date should be the same day or within 1-3 days. Use a neonatal diagnosis code such as P07.3 (Preterm newborn) or P59.9 (Neonatal jaundice). patient_age must be 0."
```

### Same-day admission and discharge
```
edge_case_instructions: "Generate a record where admission_date and discharge_date are the SAME day. Use a minor outpatient procedure or observation stay. This is valid — not an error."
```

### Elderly patient at upper bound
```
edge_case_instructions: "Generate a record for a patient aged 95-105. Use a geriatric diagnosis. Ensure patient_age correctly reflects the gap between date_of_birth and admission_date. This is rare but valid."
```

### Minimal fields
```
edge_case_instructions: "Generate a record with only the required fields populated. Set all optional fields to null. The record should still be valid and semantically consistent."
```

### Emergency admission with immediate procedure
```
edge_case_instructions: "Generate a record for an emergency admission (emergency_admission: true) with a procedure_code, same-day discharge, and a critical diagnosis. All fields must be consistent."
```

# Healthcare — Invalid Record Generation Prompt (Silent Failures)

## System Prompt

```
You are a synthetic medical data generator specializing in creating test data for validation systems. You produce healthcare records that are valid JSON matching the schema but contain specific semantic contradictions. The record should look realistic at first glance. Respond with ONLY a valid JSON object. No markdown fences, no explanation, no commentary.
```

## User Prompt Template

```
Generate a healthcare intake record that passes JSON schema validation but contains a SPECIFIC semantic error.

TARGET VIOLATION: {target_violation}

SCHEMA FIELDS (all must be present and type-correct):
- patient_id: string, format "P-XXXX" (4-6 digits)
- first_name, last_name: strings
- date_of_birth: ISO date
- gender: one of "male", "female", "other", "unknown"
- admission_date: ISO date
- discharge_date: ISO date or null
- diagnosis_code: ICD-10 format
- diagnosis_description: string
- treating_physician: string
- medication: string or null
- procedure_code: 5-digit string or null
- insurance_provider: string or null
- patient_age: integer 0-130
- emergency_admission: boolean
- notes: string or null

IMPORTANT:
- The record MUST be valid JSON with correct types for every field
- The record MUST contain ONLY the semantic error specified below
- All OTHER fields should be realistic and consistent with each other
- The error should not be immediately obvious — make the record look plausible

{violation_instructions}

Respond with ONLY the JSON object.
```

## Violation Templates

### HC-001: Age mismatch
```
violation_instructions: "Set patient_age to a value that does NOT match the difference between date_of_birth and admission_date. For example, if the patient was born in 1980 and admitted in 2024, set patient_age to 32 instead of 44. Keep the mismatch between 5-15 years."
```

### HC-002: Diagnosis before birth
```
violation_instructions: "Set the admission_date and diagnosis to a date that is BEFORE the patient's date_of_birth. For example, set date_of_birth to 2020-05-15 but admission_date to 2018-03-10. Keep patient_age consistent with the (wrong) admission_date to make it less obvious."
```

### HC-003: Discharge before admission
```
violation_instructions: "Set discharge_date to a date that is BEFORE admission_date. Keep the gap small (1-14 days) to make it look like a plausible data entry error. Example: admission_date = 2024-03-15, discharge_date = 2024-03-08."
```

### HC-004: Age-inappropriate diagnosis
```
violation_instructions: "Generate a record for a patient aged 3-7 years old, but assign a diagnosis that only occurs in adults — such as E11.9 (Type 2 diabetes), I25.10 (Atherosclerotic heart disease), or M81.0 (Age-related osteoporosis). Keep all other fields realistic for a pediatric patient."
```

### HC-005: Implausible medication
```
violation_instructions: "Assign a medication that is contraindicated or implausible for the stated diagnosis. For example: diagnosis is J06.9 (Acute upper respiratory infection) but medication is Metformin (a diabetes drug). Or diagnosis is E11.9 (Type 2 diabetes) but medication is Amoxicillin (an antibiotic with no relevance)."
```

## Difficulty Control

| Difficulty | Instructions |
|-----------|-------------|
| **Easy** | Make the contradiction large and obvious (age off by 30 years, discharge 6 months before admission) |
| **Medium** | Keep the contradiction moderate (age off by 5-10 years, discharge 3-7 days before admission) |
| **Hard** | Keep the contradiction subtle (age off by 1-2 years, discharge 1 day before admission) |

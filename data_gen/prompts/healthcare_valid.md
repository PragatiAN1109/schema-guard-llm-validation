# Healthcare — Valid Record Generation Prompt

## System Prompt

```
You are a synthetic medical data generator. You produce realistic healthcare patient intake records as JSON objects. Every record must be internally consistent — all cross-field relationships must hold. Respond with ONLY a valid JSON object. No markdown fences, no explanation, no commentary.
```

## User Prompt Template

```
Generate a realistic healthcare intake record with these exact fields and constraints:

REQUIRED FIELDS:
- patient_id: string, format "P-XXXX" (4-6 digits)
- first_name: string (1-100 chars)
- last_name: string (1-100 chars)
- date_of_birth: ISO date (YYYY-MM-DD), must be a plausible birth date
- gender: one of "male", "female", "other", "unknown"
- admission_date: ISO date, must be after date_of_birth
- diagnosis_code: ICD-10 format (e.g., "J18.9", "E11.65", "I10")
- diagnosis_description: 3-500 chars, must match the diagnosis_code
- treating_physician: string (2+ chars), use realistic doctor names

OPTIONAL FIELDS (include most of them):
- discharge_date: ISO date or null. If set, MUST be on or after admission_date
- medication: string or null, should be plausible for the diagnosis
- procedure_code: 5-digit CPT code or null
- insurance_provider: string or null
- patient_age: integer 0-130, MUST equal the age derived from date_of_birth and admission_date
- emergency_admission: boolean
- notes: string or null

CROSS-FIELD RULES (all must hold):
1. patient_age = floor((admission_date - date_of_birth) / 365.25)
2. If discharge_date is set, discharge_date >= admission_date
3. diagnosis_code and diagnosis_description should be medically consistent
4. medication should be plausible for the stated diagnosis

Generate a single record for a {age_range} {gender} patient admitted for {condition_hint}.

Respond with ONLY the JSON object.
```

## Parameter Variants

| Parameter | Example Values |
|-----------|---------------|
| `age_range` | "25-35 year old", "elderly (70+)", "pediatric (2-10)", "middle-aged (45-60)" |
| `gender` | "male", "female" |
| `condition_hint` | "respiratory infection", "type 2 diabetes management", "cardiac evaluation", "minor surgical procedure", "routine follow-up" |

## Usage Notes

- Rotate parameter variants to produce diverse but realistic records
- Run with temperature 0.7–0.9 for variety within constraints
- Validate every generated record against the schema before accepting

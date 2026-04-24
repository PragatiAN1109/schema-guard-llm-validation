# Finance — Invalid Record Generation Prompt (Silent Failures)

## System Prompt

```
You are a synthetic financial data generator specializing in test data for validation systems. You produce loan application records that are valid JSON matching the schema but contain specific semantic contradictions. The record should look realistic at first glance. Respond with ONLY a valid JSON object. No markdown fences, no explanation, no commentary.
```

## User Prompt Template

```
Generate a financial loan application record that passes JSON schema validation but contains a SPECIFIC semantic error.

TARGET VIOLATION: {target_violation}

SCHEMA FIELDS (all must be present and type-correct):
- application_id: string, format "LA-XXXXX" (5-8 digits)
- applicant_name: string
- date_of_birth: ISO date
- annual_income: number >= 0
- employment_status: one of "employed", "self_employed", "unemployed", "retired", "student"
- employer_name: string or null
- employment_length_years: number or null
- loan_amount: number 100-10000000
- loan_purpose: one of the valid enum values
- loan_term_months: one of 12, 24, 36, 48, 60, 84, 120, 180, 240, 360
- interest_rate: number or null
- credit_score: integer 300-850
- existing_debt: number >= 0
- application_date: ISO date
- approval_date: ISO date or null
- approved_amount: number or null
- property_value: number or null
- co_applicant: boolean
- notes: string or null

IMPORTANT:
- The record MUST be valid JSON with correct types
- The record MUST contain ONLY the semantic error specified
- All OTHER fields should be realistic and consistent
- The error should not be immediately obvious

{violation_instructions}

Respond with ONLY the JSON object.
```

## Violation Templates

### FN-001: Approval before application
```
violation_instructions: "Set approval_date to a date BEFORE application_date. Keep the gap small (5-30 days) to look like a plausible data entry error. Example: application_date = 2024-06-15, approval_date = 2024-05-28."
```

### FN-002: Extreme loan-to-income ratio
```
violation_instructions: "Set loan_amount to more than 30x annual_income. For example, annual_income = 45000 but loan_amount = 2500000 for a personal loan. Keep everything else realistic."
```

### FN-003: Impossible debt-to-income ratio
```
violation_instructions: "Set existing_debt so that (existing_debt + loan_amount) / annual_income > 1.0 (over 100% DTI). For example, annual_income = 60000, existing_debt = 85000, loan_amount = 40000. Keep credit_score and other fields consistent with a moderate-risk borrower."
```

### FN-004: Employment length exceeds possible working years
```
violation_instructions: "Set employment_length_years to a value that is impossible given the applicant's age. For example, date_of_birth = 2000-01-15 (age ~24) but employment_length_years = 18. The applicant would have started working at age 6."
```

### FN-005: Approved amount exceeds requested amount
```
violation_instructions: "Set approved_amount to a value HIGHER than loan_amount. For example, loan_amount = 150000 but approved_amount = 195000. This is logically inconsistent — approvals don't exceed requests."
```

## Difficulty Control

| Difficulty | Instructions |
|-----------|-------------|
| **Easy** | Extreme violation (50x income ratio, approval 6 months before application) |
| **Medium** | Moderate violation (15-30x income, approval 1-3 weeks before application) |
| **Hard** | Subtle violation (approved amount just slightly over requested, employment 1-2 years impossible) |

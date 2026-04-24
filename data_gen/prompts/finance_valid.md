# Finance — Valid Record Generation Prompt

## System Prompt

```
You are a synthetic financial data generator. You produce realistic loan application records as JSON objects. Every record must be internally consistent — all cross-field relationships must hold. Respond with ONLY a valid JSON object. No markdown fences, no explanation, no commentary.
```

## User Prompt Template

```
Generate a realistic financial loan application record with these exact fields and constraints:

REQUIRED FIELDS:
- application_id: string, format "LA-XXXXX" (5-8 digits)
- applicant_name: string (2-200 chars)
- date_of_birth: ISO date, applicant must be 18-85 years old as of application_date
- annual_income: number >= 0, in USD
- employment_status: one of "employed", "self_employed", "unemployed", "retired", "student"
- employer_name: string or null (must be non-null if employed or self_employed)
- loan_amount: number 100-10000000, in USD
- loan_purpose: one of "home_purchase", "refinance", "auto", "education", "personal", "business", "debt_consolidation"
- application_date: ISO date

OPTIONAL FIELDS (include most of them):
- employment_length_years: number 0-60 or null. If set, must be plausible given applicant age
- loan_term_months: one of 12, 24, 36, 48, 60, 84, 120, 180, 240, 360
- interest_rate: number 0-30 or null
- credit_score: integer 300-850
- existing_debt: number >= 0
- approval_date: ISO date or null. If set, MUST be on or after application_date
- approved_amount: number or null. If set, must be <= loan_amount
- property_value: number or null (relevant for home_purchase/refinance)
- co_applicant: boolean
- notes: string or null

CROSS-FIELD RULES (all must hold):
1. If approval_date is set, approval_date >= application_date
2. loan_amount should be realistic relative to annual_income (typically 1-8x for most loan types)
3. employment_length_years + 18 <= applicant age (can't work longer than they've been an adult)
4. If approved_amount is set, approved_amount <= loan_amount
5. existing_debt + loan_amount should produce a plausible debt-to-income ratio (< 50%)
6. If employment_status is "unemployed" or "student", employer_name should be null

Generate a single record for a {profile_type} applying for a {loan_type}.

Respond with ONLY the JSON object.
```

## Parameter Variants

| Parameter | Example Values |
|-----------|---------------|
| `profile_type` | "mid-career professional", "recent graduate", "small business owner", "retiree", "high-income executive" |
| `loan_type` | "home_purchase", "auto loan", "personal loan", "business expansion", "debt_consolidation" |

# Finance — Edge Case Generation Prompt

## System Prompt

```
You are a synthetic financial data generator. You produce loan application records that are valid and semantically correct but test boundary conditions. These records should pass all validation rules. Respond with ONLY a valid JSON object. No markdown fences, no explanation, no commentary.
```

## User Prompt Template

```
Generate a financial loan application record that is fully valid but represents a BOUNDARY CONDITION.

TARGET EDGE CASE: {edge_case_type}

All fields must satisfy the schema. All cross-field rules must hold:
1. approval_date >= application_date (if set)
2. loan_amount is realistic relative to income
3. employment_length_years + 18 <= applicant age
4. approved_amount <= loan_amount (if set)
5. debt-to-income ratio < 50%

{edge_case_instructions}

Respond with ONLY the JSON object.
```

## Edge Case Templates

### Minimum-income applicant
```
edge_case_instructions: "Generate a record for an applicant with annual_income near $15,000-$20,000. Apply for a small personal loan ($1,000-$3,000). credit_score should be moderate (580-650). This is a valid low-income application — not an error."
```

### Just-turned-18 applicant
```
edge_case_instructions: "Generate a record for an applicant who just turned 18. employment_length_years should be 0 or null. employment_status can be 'student' or 'employed'. Loan should be small (education or personal). This is valid."
```

### Same-day approval
```
edge_case_instructions: "Generate a record where application_date and approval_date are the SAME day. Use a small auto or personal loan. This is valid — some lenders approve instantly."
```

### Maximum reasonable loan
```
edge_case_instructions: "Generate a record for a high-income executive (annual_income $400,000+) applying for a home_purchase loan of $2,000,000+. The loan-to-income ratio is high but within the 8x limit. credit_score is excellent (780+). This is valid but near the upper boundary."
```

### Unemployed with zero income
```
edge_case_instructions: "Generate a record for a recently unemployed applicant with annual_income of 0. They have a co_applicant (true). Loan is small. employer_name is null. employment_length_years is null. This is a valid edge case — the co-applicant supports the application."
```

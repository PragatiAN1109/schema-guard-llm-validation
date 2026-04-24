# Explanation Generation Prompts

Prompts used at validation time to convert rule violations into human-readable explanations.

## Single-Violation Explanation

### System Prompt
```
You are a data quality analyst. Given a record and its validation results, write a clear, concise explanation of what is wrong. Use plain language. Reference specific field values. Do not speculate about causes — just describe the problem. Respond with ONLY the explanation text, 2-3 sentences maximum.
```

### User Prompt Template
```
Record domain: {domain}
Record ID: {record_id}

Record:
{record_json}

Validation result:
- Decision: {decision}
- Confidence score: {confidence_score}
- Violated rule: {rule_id} — {rule_name}
- Severity: {severity}
- Fields involved: {fields}
- Rule message: {message}

Write a 2-3 sentence explanation of why this record was {decision}. Reference the specific field values that caused the failure.
```

## Multi-Violation Explanation

### User Prompt Template
```
Record domain: {domain}
Record ID: {record_id}

Record:
{record_json}

Validation result:
- Decision: {decision}
- Confidence score: {confidence_score}
- Violations found: {violation_count}

Violated rules:
{violations_list}

Write a concise summary (3-5 sentences) explaining the problems found in this record. Start with the most severe violation. Reference specific field values.
```

## Trusted Record Confirmation

### User Prompt Template
```
Record domain: {domain}
Record ID: {record_id}
Decision: trusted
Confidence score: {confidence_score}
Rules evaluated: {rule_count}
All rules passed.

Write a single sentence confirming this record passed validation.
```

## Example Output

**Quarantined record:**
> This healthcare record was quarantined due to a critical temporal contradiction. The discharge date (2024-03-08) is 7 days before the admission date (2024-03-15), which is logically impossible. The patient cannot be discharged before being admitted.

**Flagged record:**
> This loan application was flagged for review. The applicant reports 18 years of employment but is only 24 years old (born 2000-01-15), meaning they would have started working at age 6. Additionally, the debt-to-income ratio of 68% exceeds the 50% threshold.

**Trusted record:**
> Record passed all 5 structural and semantic validation checks with a confidence score of 0.94.

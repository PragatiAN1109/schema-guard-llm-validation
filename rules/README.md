# rules/

Semantic rule engine for cross-field validation.

## How It Works

Each rule is a Python function registered with the `RuleRegistry`. Rules are domain-scoped — healthcare rules only run against healthcare records, finance rules only run against finance records.

## Rule Interface

Every rule function follows the same contract:

**Input:** A record dictionary (the JSON record being validated).

**Output:** A `RuleResult` dict with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `rule_id` | string | Unique identifier (e.g., `HC-003`, `FN-002`) |
| `rule_name` | string | Human-readable name |
| `passed` | boolean | Whether the record satisfies this rule |
| `severity` | string | `critical`, `warning`, or `info` |
| `fields` | list[string] | Fields involved in this check |
| `message` | string | Explanation of the violation (empty if passed) |

## Rule Registration

Rules are registered by domain using the `@register_rule` decorator:

```python
@register_rule(domain="healthcare_intake", rule_id="HC-003", severity="critical")
def discharge_after_admission(record: dict) -> RuleResult:
    ...
```

## Planned Rules

**Healthcare (HC-xxx):**
- HC-001: Patient age matches date of birth vs admission date
- HC-002: Diagnosis date is after date of birth
- HC-003: Discharge date is after admission date
- HC-004: Age-appropriate diagnosis codes
- HC-005: Medication plausibility for diagnosis category

**Finance (FN-xxx):**
- FN-001: Approval date is after application date
- FN-002: Loan-to-income ratio within limits
- FN-003: Debt-to-income ratio within limits
- FN-004: Employment length plausible given applicant age
- FN-005: Approved amount does not exceed requested amount (if set)

## Files

- `rule_registry.py` — Registry class, decorator, rule runner
- `healthcare_rules.py` — Healthcare domain rules (future)
- `finance_rules.py` — Finance domain rules (future)

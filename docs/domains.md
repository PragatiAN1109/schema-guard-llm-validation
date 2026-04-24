# Domain Selection

SchemaGuard validates two domains: **healthcare intake records** and **financial/loan application records**.

## Why Healthcare Intake

Healthcare records have natural cross-field dependencies that are easy to define and impossible to catch with schema validation alone:

- **Temporal rules** — diagnosis date must follow birth date, discharge must follow admission, procedure dates must fall within admission window
- **Age-derived constraints** — pediatric diagnoses on elderly patients, age-impossible conditions
- **Categorical consistency** — medication and procedure codes that only apply to certain diagnosis categories

These rules are intuitive. Anyone reviewing the system immediately understands why "diagnosis before birth" is wrong. That makes evaluation straightforward and demo results easy to present.

## Why Financial / Loan Applications

Finance records introduce a different class of constraints that complement healthcare:

- **Ratio-based rules** — debt-to-income limits, loan-to-value caps, approved amount relative to income
- **Policy constraints** — employment length vs. applicant age, minimum income for loan tiers
- **Temporal ordering** — application date before approval date, employment start before application

Financial rules are numeric thresholds — easy to test, easy to measure, and easy to justify without domain expertise.

## Why These Two Together

The combination covers temporal logic, numeric ratios, categorical consistency, and boundary handling. This demonstrates that SchemaGuard's architecture is domain-agnostic: the rule engine and validation pipeline work identically regardless of domain. Only the schemas and rule definitions change.

Both domains are realistic, evaluable by inspection, and manageable for a solo developer.

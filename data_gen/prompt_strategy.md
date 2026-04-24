# Prompt Strategy

## Why Structured Prompting

LLMs default to conversational output. When generating synthetic evaluation data, every response must be machine-parseable JSON that conforms to a specific schema. Structured prompting solves this by embedding the schema definition, field constraints, and output format directly into the prompt — eliminating freeform text, markdown wrappers, and commentary from the response.

Without structured prompting, generated records require brittle post-processing to extract JSON, and the error rate on schema compliance increases significantly.

## Enforcing JSON-Only Output

Every generation prompt includes:

1. An explicit instruction: "Respond with ONLY a valid JSON object. No markdown, no explanation, no commentary."
2. The complete field list with types and constraints
3. A concrete example of the expected output format
4. A closing instruction reinforcing JSON-only output

This triple-fence approach (instruction → schema → reinforcement) keeps compliance above 95% across providers.

## Valid vs. Invalid Prompt Design

**Valid prompts** tell the model to generate a realistic, self-consistent record. The prompt includes all cross-field constraints explicitly:
- "discharge_date must be after admission_date"
- "patient_age must match the difference between date_of_birth and admission_date"
- "loan_amount should be a realistic multiple of annual_income"

**Invalid prompts** flip this. They instruct the model to generate a record that passes schema validation but violates one or more specific semantic rules. The prompt names the exact contradiction to inject:
- "Set discharge_date to a date BEFORE admission_date"
- "Set loan_amount to more than 50x annual_income"

The key: invalid prompts ask for a single, controlled violation while keeping everything else realistic. This produces records that look plausible on casual inspection but fail semantic checks — exactly the kind of silent failure SchemaGuard is designed to catch.

## Edge Case Generation

Edge-case prompts target boundary conditions that are technically valid but stress the rule engine:
- Newborn patient (age 0, admission_date near date_of_birth)
- Same-day admission and discharge
- Minimum-income applicant with a small personal loan
- Applicant at exactly age 18 with 0 years employment

These records should pass all rules. If the rule engine incorrectly flags them, that reveals false-positive weaknesses.

## Semantic Contradiction Injection

Each invalid prompt targets a specific rule from the rule registry (HC-001 through HC-005, FN-001 through FN-005). The prompt template includes a `target_violation` parameter that controls which contradiction to inject.

This makes the dataset systematically testable: for each rule, there are records specifically designed to trigger it, and labels confirm which rule was targeted.

## Explanation Prompts

After validation, flagged records need human-readable explanations. Explanation prompts take the record, the violated rules, and the field values as input, then ask the LLM to produce a plain-language summary of what went wrong.

These prompts are separate from generation prompts and run at validation output time, not at data creation time. They follow a fill-in-the-blank structure:
- "Given this record: {record_json}"
- "The following rules were violated: {violations}"
- "Write a 2-3 sentence explanation of what is wrong and why this record was {decision}."

This keeps explanations grounded in actual validation results rather than hallucinated.

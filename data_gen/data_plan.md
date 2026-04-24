# Data Generation Plan

## Record Types

| Type | Description | Purpose |
|------|-------------|---------|
| **Valid** | Structurally and semantically correct | Baseline — system should score high and route to trusted |
| **Invalid (silent failure)** | Schema-valid JSON with semantic contradictions | Core test — system must detect cross-field violations |
| **Edge case** | Boundary values that are plausible but stress-test rules | Robustness — system should handle near-boundary records correctly |

## Target Dataset Size

| Domain | Total Records | Valid (60%) | Invalid (25%) | Edge Case (15%) |
|--------|--------------|-------------|---------------|-----------------|
| Healthcare intake | 300 | 180 | 75 | 45 |
| Financial loan application | 300 | 180 | 75 | 45 |

## Generation Method

All records generated via LLM using domain-specific prompt templates. Each prompt type has a separate template:

- **Valid prompts** — include full schema, cross-field constraints, and instructions to produce realistic self-consistent records
- **Invalid prompts** — specify exactly which semantic rule to violate while keeping all other fields valid
- **Edge-case prompts** — target boundary conditions (newborns, minimum income, same-day admit/discharge, max-age applicants)

## Labeling Format

Every generated record is stored with metadata:

```json
{
  "record_id": "HC-gen-0042",
  "domain": "healthcare_intake",
  "record": { ... },
  "labels": {
    "structural_valid": true,
    "semantic_valid": false,
    "violated_rules": ["HC-003"],
    "prompt_type": "invalid",
    "target_violation": "discharge_before_admission",
    "difficulty": "medium"
  }
}
```

## Difficulty Levels

| Level | Definition |
|-------|-----------|
| **Easy** | Obvious contradiction (discharge 6 months before admission) |
| **Medium** | Plausible but wrong (discharge 1 day before admission) |
| **Hard** | Subtle violation requiring careful cross-field reasoning |

## Storage

- Raw generated output: `data_gen/datasets/raw/`
- Labeled and verified: `data_gen/datasets/labeled/`
- Format: JSONL (one record per line)

## Quality Checks

- Manual review of 50+ records per domain to confirm label accuracy
- Cross-check that labeled violations actually trigger the corresponding rule
- Document any LLM generation artifacts or failure modes in `data_gen/generation_notes.md`

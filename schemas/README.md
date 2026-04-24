# schemas/

JSON Schema Draft 7 definitions for each supported domain.

| File | Domain | Required Fields | Total Properties |
|------|--------|----------------|-----------------|
| `healthcare_schema.json` | Healthcare intake | 9 | 16 |
| `finance_schema.json` | Financial loan application | 9 | 19 |

Schemas enforce types, formats, patterns (ICD-10, ID formats), enums, and numeric ranges. `additionalProperties: false` on both.

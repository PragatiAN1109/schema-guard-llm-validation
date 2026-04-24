# Project Overview

**SchemaGuard** is a semantic compliance and drift detection layer for LLM-generated structured outputs.

## The Problem

LLMs generating structured JSON can produce output that passes schema validation but is semantically wrong. A healthcare record with a discharge date before the admission date is valid JSON with valid types — but it's nonsense. A loan approval for 50x the applicant's income clears every type check. These silent failures propagate into databases and decisions without triggering a single alert.

## What SchemaGuard Does

It sits between the LLM output and any downstream consumer. Every record goes through three checks:

1. **Structural validation** — schema compliance (types, required fields, formats, ranges)
2. **Semantic validation** — cross-field rule checks (date ordering, ratio limits, categorical consistency)
3. **Drift detection** — statistical monitoring of output distributions over time

Each record gets a confidence score and a routing decision: **trusted**, **flagged**, or **quarantined**. Flagged and quarantined records include plain-language explanations of what went wrong.

## Where This Applies

Any system that uses LLM-generated structured data in production:

- Data pipelines ingesting LLM-extracted records
- Automated form processing in healthcare or finance
- Quality gates in ML training data generation
- Compliance monitoring for regulated-industry outputs
- Continuous monitoring of LLM behavior in deployed applications

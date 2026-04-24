# Networking Pitch — SchemaGuard

---

## 30-Second Version

"I recently built a project called SchemaGuard. It's a validation layer for LLM-generated structured data — things like patient records or loan applications that come out as JSON.

The issue is that LLMs produce output that passes schema validation but contains logical errors — like a discharge date before an admission date. Schema checks don't catch that. SchemaGuard does, using cross-field semantic rules, confidence scoring, and drift detection. It routes every record to trusted, flagged, or quarantined with a full audit trail.

I built the full stack — rule engine, validation pipeline, FastAPI API, Streamlit demo, and an evaluation pipeline. Two domains: healthcare and finance."

---

## 60-Second Version

"So I've been working on a project called SchemaGuard that addresses a real gap in LLM-powered data pipelines.

When you use an LLM to generate structured JSON — patient intake forms, loan applications, configuration records — the output almost always passes schema validation. Types are correct, fields are present, formats match. But the data can be logically wrong. A healthcare record where a 5-year-old is diagnosed with age-related osteoporosis. A loan approved for 52 times someone's income. These pass every type check but they're semantically broken.

I built a validation layer that catches these. It runs 10 cross-field semantic rules across healthcare and finance domains — things like 'discharge must be after admission' and 'employment length must be plausible for the applicant's age.' Each record gets a confidence score from 0 to 1 and gets routed to trusted, flagged, or quarantined.

There's also a drift detection module. If the LLM starts generating different patterns over time — younger patients, higher incomes — the system detects that by comparing batch distributions against a baseline.

I built a FastAPI REST API, a Streamlit demo UI, and a full evaluation pipeline. On the seed data, it achieves 100% accuracy with zero false quarantines. The interesting part is that it's all deterministic — same input, same output, full rule trace. Which matters in healthcare and finance where you need auditability."

---

## Follow-Up Lines (if they ask more)

**"What's the tech stack?"**
"Python, FastAPI for the API, jsonschema for structural validation, a custom decorator-based rule engine for semantic checks, and Streamlit for the demo. Drift detection uses z-scores and PSI. Storage is JSON and SQLite — keeps it simple to run locally."

**"Where did the idea come from?"**
"I kept seeing discussions about LLM output quality, and the solutions were always about better prompting or fine-tuning. But nobody was talking about what happens when the output *looks* right but isn't. Schema validation gives a false sense of security. I wanted to build the layer that fills that gap."

**"What would you do next with it?"**
"Two things: first, scale the evaluation dataset using LLM generation — I have the prompt templates, just need to connect a provider. Second, add a lightweight RAG layer where the explanation prompts are grounded in retrieved rule documentation. The architecture already supports it."

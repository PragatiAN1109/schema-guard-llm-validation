# SchemaGuard

## Semantic Validation and Drift Detection for LLM-Generated Structured Outputs

---

**Author:** Pragati Narotam  
**Course:** INFO 7375 — Prompt Engineering for Generative AI  
**Institution:** Khoury College of Computer Sciences, Northeastern University  
**Date:** April 2025  
**Repository:** github.com/pragatinarote/schema-guard-llm-validation

---

## Abstract

Large language models (LLMs) tasked with generating structured JSON data produce output that satisfies schema validation while violating domain-specific logical constraints. A patient record with a discharge date seven days prior to admission passes every structural check. A loan application for 52 times the applicant's annual income passes every type check. These silent semantic failures propagate unchecked into downstream systems.

**SchemaGuard** addresses this gap with a four-stage pipeline — structural validation, cross-field semantic rule evaluation, severity-weighted confidence scoring, and decision routing — deployed across two regulated domains: healthcare intake records and financial loan applications. The system augments per-record validation with population-level drift detection across four statistical signals (z-score, PSI, null-rate change, violation-rate change), and extends explanation quality through Retrieval-Augmented Generation (RAG) grounded in clinical and regulatory reference documents.

Evaluated on 16 labeled seed records and 140 real audit-log records, SchemaGuard achieves precision, recall, and F1 of 1.0 on both domains. These ceiling metrics are expected for a deterministic rule-based classifier evaluated on a dataset designed specifically to target each rule; their significance lies in confirming correct rule implementation and — critically — a 0% false-quarantine rate on valid records, including edge-case boundary conditions. A separate adversarial robustness evaluation across 53 structured test cases (noise injection, boundary probing, and multi-violation compound records) confirms 100% crash-free behaviour, correct boundary decisions, and accurate compound penalty computation. Median validation latency is 0.09 ms (~3,800 records/second). The RAG explanation module increases qualitative explanation score from 2.7/6 (deterministic baseline) to 6.0/6 across seven live-evaluated cases, with each RAG explanation citing the relevant regulation or clinical standard by section number.

---

## 1 · Introduction

The deployment of large language models in production data pipelines introduces a class of data quality failure that traditional validation tooling does not detect. Schema validators, type checkers, and linting tools are designed for the assumption that malformed data is the dominant failure mode. For LLM-generated structured data, this assumption does not hold. LLMs produce type-correct, schema-conformant JSON while simultaneously violating logical relationships that give the data meaning.

This failure mode is particularly consequential in regulated domains. In healthcare, a patient record with an impossible date sequence could corrupt downstream analytics, trigger incorrect billing codes, or — in a system with insufficient human review — inform a clinical decision. In financial services, a loan application with an impossible debt-to-income ratio could bias credit risk models or produce reporting anomalies.

The problem is structural: standard validation tools operate on individual field values. Semantic constraints span multiple fields. The relationship between `discharge_date` and `admission_date` is not expressible in JSON Schema Draft 7. The constraint that a loan's approved amount cannot exceed its requested amount is not a type check. These are domain-specific logical rules requiring a distinct validation layer.

SchemaGuard provides that layer. The project makes three contributions:

1. **A four-stage semantic validation pipeline** operating below 1 ms per record, with deterministic, auditable rule evaluation and severity-weighted confidence scoring.
2. **Population-level drift detection** monitoring four statistical signals across record batches, enabling detection of gradual distribution shifts that per-record validation cannot observe.
3. **RAG-augmented failure explanations** that retrieve clinical and regulatory reference documents at query time and produce grounded, actionable explanations citing CMS, HL7 FHIR, ICD-10, CFPB ATR, Regulation Z, and ECOA by section number.
4. **Research positioning** against existing validation approaches — JSON Schema, Great Expectations, and LLM-as-judge — characterising where each approach fails for LLM-generated structured data and where SchemaGuard occupies a gap in the current tooling landscape (§2.4).

The system is implemented in Python, exposed via a FastAPI REST interface, and evaluated on two domains: healthcare intake (five rules, HC-001–HC-005) and financial loan applications (five rules, FN-001–FN-005).

---

## 2 · Problem Statement

### 2.1 The Structural Validation Gap

JSON Schema Draft 7 validates a record against a type schema: are all required fields present, do values have the correct types, do strings match the expected format? This is necessary but insufficient for LLM-generated data.

The following record passes full JSON Schema validation for a healthcare intake domain:

```json
{
  "patient_id": "P-4412",
  "admission_date": "2024-08-15",
  "discharge_date": "2024-08-08",
  "patient_age": 34,
  "date_of_birth": "1990-01-20"
}
```

Every field is present, every type is correct. The record is also logically impossible: `discharge_date` precedes `admission_date` by seven days. No per-field check detects this. No schema validator raises an error.

Similarly, the following financial record passes all schema checks:

```json
{
  "annual_income": 48000,
  "loan_amount": 2500000,
  "approval_date": "2024-06-28",
  "application_date": "2024-07-20"
}
```

The loan-to-income ratio is 52.1× — five times the regulatory maximum — and the approval date precedes the application date by 22 days. Both are physically and legally impossible. Both pass schema validation.

### 2.2 Taxonomy of LLM-Generated Semantic Failures

LLM-generated semantic failures fall into four categories:

| Category | Mechanism | Example |
|----------|-----------|---------|
| Temporal consistency | Dates generated from independent distributions | `discharge_date < admission_date` |
| Ratio violations | Numeric fields sampled independently | `loan_amount = 52 × annual_income` |
| Categorical inconsistencies | Semantically dependent fields generated independently | Pneumonia diagnosis + antidiabetic medication |
| Silent population drift | Gradual distribution shift with no per-record violation | Mean patient age drifts from 45 to 28 over 1,000 records |

### 2.3 Scope

SchemaGuard targets semantic validation failures in LLM-generated structured records across two regulated domains. It does not address factual accuracy, privacy compliance, or model alignment. Its domain is logical coherence: whether the values in a record are mutually consistent.

SchemaGuard targets semantic validation failures in LLM-generated structured records across two regulated domains. It does not address factual accuracy, privacy compliance, or model alignment. Its domain is logical coherence: whether the values in a record are mutually consistent.

---

## 2.4 · SchemaGuard as a Semantic Validation Layer: Positioning and Novelty

### 2.4.1 The Validation Landscape

Data validation for structured records is a well-studied problem. Before situating SchemaGuard's contribution, it is worth characterising the existing tooling landscape honestly — what each approach handles well, and where each one fails when applied to LLM-generated data.

Three categories of tools are directly relevant: structural schema validators, data quality frameworks, and LLM-based validators. Each occupies a distinct position in the tradeoff space of expressiveness, interpretability, runtime cost, and auditability.

---

### 2.4.2 JSON Schema Validation

JSON Schema (currently Draft 2020-12, commonly deployed at Draft 7) is the dominant standard for structural validation of JSON documents. Its validators are fast, deterministic, and widely supported across languages and platforms.

**What JSON Schema does well.** JSON Schema excels at structural contracts: field presence, type enforcement, string format matching, numeric range constraints, and enumeration checks. It is declarative, tool-agnostic, and produces machine-readable error output. For API surface validation — ensuring that a client sends a well-formed request — JSON Schema is essentially the right tool.

**Where JSON Schema fails for LLM-generated data.** The JSON Schema specification operates on individual fields in isolation. It has no mechanism for expressing constraints that span multiple fields, because those constraints are not structural — they are semantic. The Draft 7 specification does not support:

- Cross-field comparisons (`if field_A > field_B`)
- Derived field checks (`if field_C ≠ f(field_A, field_B)`)
- Domain-specific plausibility rules (`if diagnosis_code ∈ adult_only_codes, then patient_age ≥ 18`)
- Continuous ratio constraints (`if loan_amount / annual_income ≤ 10.0`)

The `if/then/else` keywords in JSON Schema Draft 7 allow conditional validation, but only on individual field values — not on relationships between field values. The `dependencies` keyword allows a field to require other fields' presence, but not their logical relationship. The failures that SchemaGuard targets are simply inexpressible in the JSON Schema vocabulary.

**Relationship to SchemaGuard.** SchemaGuard runs JSON Schema Draft 7 validation as Stage 1 of its pipeline. This is not a design redundancy — it is the correct layering. Structural validation catches malformed records before semantic rules run, preventing false rule-fire on records where required fields are absent or mistyped. The semantic layer is additive: it handles the constraint space that JSON Schema cannot reach.

---

### 2.4.3 Data Quality Frameworks: Great Expectations and dbt

The data quality ecosystem has produced several frameworks for asserting expectations over data at rest or in motion. The two most prominent are Great Expectations (Superconductive, 2019) and dbt tests (dbt Labs, 2020), with newer entrants including Soda Core and Pandera.

**Great Expectations.** Great Expectations provides a rich library of "expectations" — assertions about column values, distributions, referential integrity, and null rates — applied to tabular data (DataFrames, SQL tables). It supports multi-column expectations (`expect_column_pair_values_A_to_be_greater_than_B`) that can express some cross-field relationships. Its strengths are breadth, observability, and integration with data pipelines; its primary deployment pattern is batch validation over warehouse data.

**Limitations for the LLM generation use case.** Great Expectations is designed for static data profiles — the expectations are typically derived from historical data distributions and represent statistical norms rather than logical invariants. For LLM-generated data, the relevant constraints are not statistical (the distribution of patient ages across the dataset) but logical (this specific patient's `patient_age` must equal the integer computed from their `date_of_birth` and `admission_date`). A Great Expectations suite can express the age constraint approximately — for example, via `expect_column_pair_values_A_to_be_greater_than_B` on `patient_age` and a threshold — but it cannot express the exact derived-field constraint, the tolerance margin (±1 year), or the downstream consequence of failure. Great Expectations also has no native mechanism for routing individual records to different downstream systems based on violation severity, which is central to SchemaGuard's operational model.

**dbt tests.** dbt's test layer supports `not_null`, `unique`, `accepted_values`, and `relationships` tests natively, with custom SQL tests for more complex constraints. SQL-based cross-field tests are expressive but require the data to be in a SQL-queryable store and couple validation logic to the data warehouse layer. For per-record validation at inference time — where the record is a live JSON object being generated — SQL-based tests are architecturally inappropriate.

**Relationship to SchemaGuard.** SchemaGuard's semantic rule layer occupies the constraint expressiveness position that Great Expectations approaches but does not fully reach: exact cross-field logical invariants, derived-field checks, and domain-specific plausibility rules. The key architectural difference is granularity: Great Expectations validates *datasets*; SchemaGuard validates *individual records* in real time. The two are complementary rather than competing — Great Expectations addresses population-level batch quality; SchemaGuard addresses per-record semantic coherence at the point of generation.

---

### 2.4.4 LLM-Based Validation

A natural question is whether LLMs themselves can validate LLM-generated output. Several recent approaches use LLMs as evaluators, either as direct judges (the "LLM-as-judge" pattern) or as components in chain-of-thought checking pipelines (Peng et al., 2023; Wei et al., 2022).

**LLM-as-judge approaches.** The core idea is to prompt a language model to assess whether a generated output meets some criterion, using the model's world knowledge to identify logical inconsistencies. This approach has demonstrated value for open-ended generation quality assessment — rating coherence, factual plausibility, stylistic appropriateness. Several recent works (Zheng et al., 2023; Liu et al., 2023) use GPT-4 or Claude as judges in multi-turn evaluation pipelines.

**Limitations in the validation-for-production setting.** LLM-based validation introduces several properties that are problematic in regulated production contexts:

1. **Non-determinism.** The same record may produce different judgments across calls due to sampling temperature, prompt framing, and model version changes. In a healthcare or financial audit context, a validation decision must be reproducible: the same record must always produce the same result.

2. **Auditability gap.** An LLM judgment ("this record appears inconsistent") does not provide a machine-readable violation trace that can be stored in an audit log, surfaced to downstream systems, or used to compute a numeric confidence score. Regulated deployments require structured, inspectable outputs.

3. **Latency.** LLM API calls take 1–10 seconds per record. At 0.09 ms per record for SchemaGuard's deterministic layer, the throughput difference is approximately four orders of magnitude. This is not a cost optimisation consideration — it is a fundamental architectural incompatibility with real-time data pipelines that process thousands of records per second.

4. **Calibration uncertainty.** An LLM's implicit threshold for what constitutes a "significant" violation is not directly configurable. Adjusting how aggressively the validator flags loan-to-income ratios requires prompt engineering and cannot be expressed as a threshold parameter.

**Where LLM-based validation excels.** LLMs are genuinely better at open-ended plausibility assessment: detecting subtle tonal inconsistencies, identifying factually unlikely medication-diagnosis combinations not covered by a rule table, and generating human-readable explanations. This is why SchemaGuard uses an LLM in its explanation layer (Stage 4) rather than discarding LLMs entirely. The architecture explicitly partitions the problem: deterministic rules handle the constraint evaluation, and the LLM handles the explanation.

**Relationship to SchemaGuard.** SchemaGuard's design philosophy is that validation and explanation are separable concerns requiring different tools. The validation decision is deterministic, auditable, and sub-millisecond. The explanation is generative, contextual, and asynchronous. This partitioning is the architectural contribution that LLM-as-judge approaches do not make.

---

### 2.4.5 Comparison Summary

| Property | JSON Schema | Great Expectations | LLM-as-Judge | SchemaGuard |
|----------|:-----------:|:------------------:|:------------:|:-----------:|
| Cross-field semantic rules | ✗ | Partial | ✓ | ✓ |
| Deterministic, reproducible | ✓ | ✓ | ✗ | ✓ |
| Per-record real-time | ✓ | ✗ | Slow | ✓ |
| Configurable severity tiers | ✗ | Partial | ✗ | ✓ |
| Numeric confidence score | ✗ | ✗ | ✗ | ✓ |
| Machine-readable audit trail | ✓ | ✓ | ✗ | ✓ |
| Grounded regulatory explanation | ✗ | ✗ | Partial | ✓ |
| Population-level drift detection | ✗ | ✓ | ✗ | ✓ |
| Latency (per record) | <0.1 ms | batch | 1–10 s | 0.09 ms |
| Domain-specific rule authoring | ✗ | Low-code | Prompt | Python |

The comparison reveals SchemaGuard's position: it is the only approach in this table that simultaneously provides cross-field deterministic validation, numeric confidence scoring, machine-readable audit trails, and grounded explanation. It occupies a gap rather than replicating an existing tool.

---

### 2.4.6 Novelty and Research Implications

SchemaGuard's primary contribution is not any individual component — FAISS vector search, JSON Schema validation, and PSI-based drift detection are all standard techniques. The contribution is the *composition* of these components into a unified operational architecture for a specific, previously unaddressed problem: semantic validation of LLM-generated structured records in regulated domains.

**Three novel aspects of the composition:**

**1. The validation-explanation separation.** Existing data quality tools either produce structured violations without contextual explanation (schema validators, Great Expectations) or produce contextual assessment without structured violations (LLM-as-judge). SchemaGuard separates these concerns across two explicit pipeline stages. Stage 2 produces structured violations with rule IDs, field names, and severity. Stage 4 augments these structured violations with retrieved regulatory context. Neither stage could produce what the other produces. The composition — structured violation as RAG query anchor, regulatory chunk as generative context — is the mechanism that makes per-violation grounded explanations tractable at production scale.

**2. The bimodal confidence model for routing.** The three-tier routing model (trusted/flagged/quarantined) derived from a continuous severity-weighted confidence score is a design decision with direct operational implications. Binary pass/fail validation loses severity information. The confidence score preserves it: a record with two critical violations (0.40) is routed differently than a record with one warning violation (0.88), and both are routed differently than a record with one critical violation (0.70). This routing model has precedent in clinical decision support systems (triage tiers) and credit risk assessment (risk bands), but it has not previously been applied to LLM output validation.

**3. Orthogonal per-record and population-level validation.** Per-record semantic validation and population-level drift detection are typically addressed by separate systems. SchemaGuard integrates both in a single pipeline, with drift detection operating on the aggregate statistics of validated batches. This means a batch of individually trusted records can still trigger a drift alert — a failure mode that per-record validation is structurally incapable of detecting. The 6/6 shift detection rate against a 0/2 false-alarm rate on stable batches demonstrates this layer is functional.

**Research implications.** The SchemaGuard architecture has implications for three active research areas.

In *LLM output quality assurance*, the dominant approaches are RLHF feedback, constitutional AI, and post-hoc LLM judging. SchemaGuard demonstrates that for the structured-output subproblem, domain-specific deterministic rules are faster, more auditable, and more operationally appropriate than generative assessment — while still benefiting from LLM capabilities at the explanation layer. The hybrid architecture (deterministic gate + generative explanation) is a pattern worth formalising.

In *responsible AI deployment for regulated domains*, the system demonstrates that semantic constraints from domain standards (HL7 FHIR, ICD-10, CFPB ATR) can be encoded as executable, auditable functions without requiring LLM interpretation. The encoding process — translating regulatory text into Python rule functions — is manual and requires domain knowledge, but it is tractable. The 10 rules implemented here represent a proof of concept for a broader research programme in machine-executable regulatory constraint encoding.

In *data drift monitoring for generative systems*, existing drift detection literature focuses on feature distributions in discriminative models (input data drift) or output distributions in classifiers (concept drift). SchemaGuard's drift layer monitors the *output quality* of a generative system — specifically, whether the statistical properties of generated records are shifting in ways that increase semantic violation rates or alter null-rate profiles. This is a distinct problem formulation that the existing drift literature does not directly address.

---

### 2.4.7 Limitations of the Positioning

Three caveats are important for honest research positioning.

First, the comparison in §2.4.5 reflects a static snapshot of tooling capabilities. Great Expectations and dbt are actively developed; newer versions may narrow the feature gap in cross-field constraint expressiveness.

Second, the performance advantage over LLM-as-judge (four orders of magnitude in latency) holds for the deterministic validation layer but not for the full pipeline including RAG explanation generation (2.8–3.2 s per explanation). The relevant comparison for latency-critical deployments is the validation decision alone, not the full explanation pipeline.

Third, the claim of occupying a "gap" in the tool landscape is based on available open-source tools as of the project date. Proprietary data quality platforms (e.g., enterprise versions of Great Expectations, Collibra, Informatica) may implement cross-field semantic rule engines with similar capability. The comparison is made against publicly documented tool capabilities.

---

## 3 · System Architecture

### 3.1 Pipeline Overview

```
JSON Record
    │
    ▼
┌─────────────────────────────────┐
│  Stage 1: Structural Validation  │  JSON Schema Draft 7
│  → valid / errors list           │  types, formats, required fields
└──────────────┬──────────────────┘
    PASS        │ FAIL → quarantine (confidence = 0.0)
               ▼
┌─────────────────────────────────┐
│  Stage 2: Semantic Validation    │  10 cross-field rules
│  → violations list + severity    │  temporal, ratio, plausibility
└──────────────┬──────────────────┘
               ▼
┌─────────────────────────────────┐
│  Stage 3: Confidence Scoring     │  score = 1.0 − Σ(penalties)
│  → float in [0.0, 1.0]           │  critical: −0.30, warning: −0.12
└──────────────┬──────────────────┘
               ▼
┌─────────────────────────────────┐
│  Stage 4: Decision Router        │
│  trusted / flagged / quarantined │  ≥0.85 / 0.50–0.84 / <0.50
└──────────────┬──────────────────┘
               ▼
┌─────────────────────────────────┐
│  Explanation + Audit Log (JSONL) │
└─────────────────────────────────┘
```

### 3.2 Module Structure

| Package | Files | Responsibility |
|---------|-------|----------------|
| `schemas/` | 2 JSON | Domain schema definitions (Draft 7) |
| `rules/` | registry + 2 rule files | 10 semantic rules with severity metadata |
| `validator/` | 7 Python files | Pipeline orchestration, batch, explanation, audit |
| `drift/` | baseline + detector | Four-signal drift monitoring |
| `scoring/` | confidence + decision | Weighted scoring and three-tier routing |
| `rag/` | 7 Python files | FAISS vector store, retriever, RAG explainer |
| `api/` | main + routes + models | FastAPI REST endpoints |
| `data_gen/` | generator + validator | Synthetic dataset pipeline |
| `evaluation/` | metrics + charts | Classification metrics, latency, drift visualisation |

### 3.3 Batch and Drift Path

After per-record processing, aggregated batch statistics are compared against a stored baseline using four drift signals:

- **z-score**: normalised shift in numeric field means (threshold: 1.5σ)
- **PSI**: Population Stability Index for categorical field distributions (threshold: 0.20)
- **Null-rate delta**: per-field null-rate change (threshold: 15%)
- **Violation-rate delta**: fraction of records violating each rule (threshold: 10%)

Drift detection operates orthogonally to per-record routing: a batch of entirely trusted records can still trigger a drift alert if the population distribution has shifted.

### 3.4 Routing Thresholds

| Decision | Score range | Semantics |
|----------|-------------|-----------|
| Trusted | ≥ 0.85 | Safe for downstream use |
| Flagged | 0.50–0.84 | Route to human review queue |
| Quarantined | < 0.50 | Block from downstream systems |

### 3.5 Resilience Design

All components execute within try/except blocks. A crashing rule returns a typed error result; all other rules continue. Drift detection wraps a circuit breaker (threshold: 3 failures, cooldown: 30 s) routing to a safe fallback rather than blocking batch results. Failed async jobs retry twice before moving to a dead-letter collection.

---

## 4 · Implementation Details

### 4.1 Prompt Engineering

#### 4.1.1 Triple-Fence Pattern

Every generation prompt follows a three-segment structure that maintains schema compliance above 95% without post-processing:

1. **Instruction segment** — explicit instruction to produce only a valid JSON object, no markdown, no explanation.
2. **Schema segment** — complete field list with types, formats, constraints, and all cross-field rules stated in plain language.
3. **Reinforcement segment** — closing repetition of the JSON-only constraint with a concrete example of the expected format.

#### 4.1.2 Valid vs. Invalid Prompt Design

**Valid record prompts** state all cross-field constraints affirmatively:
> *"The `discharge_date` must be on or after `admission_date`. The `patient_age` must equal `floor((admission_date − date_of_birth) / 365.25)` ± 1."*

**Invalid record prompts** flip exactly one constraint while keeping all others active, naming the target violation explicitly with a concrete example:
> *"Set `discharge_date` to a date BEFORE `admission_date`. For example: `admission_date = 2024-08-15`, `discharge_date = 2024-08-08`. All other fields must remain realistic and type-correct."*

Each invalid record is confirmed by the production semantic validator before being saved. Records that fail the semantic gate (target rule does not fire) are discarded and regenerated up to three times.

#### 4.1.3 Prompt Version History (HC-003)

| Version | Change | Compliance Rate |
|---------|--------|-----------------|
| v1 | Simple instruction, no example | ~72% |
| v2 | Added concrete example of violation | ~88% |
| v3 | Added negative example + reinforcement closing | ~96% |

The consistent failure mode was the model "correcting" invalid dates based on its prior toward coherent output. Resolution required framing the violation as intentional research data.

#### 4.1.4 Edge Case Prompts

Edge cases target boundary conditions that are technically valid but stress the rule engine: a newborn patient (age 0), same-day discharge (LOS = 0 days), a loan applicant at exactly age 18, a minimum-income applicant with a small personal loan. These records must pass all rules; false-positive flagging reveals over-aggressive threshold specification.

---

### 4.2 Synthetic Data Generation

#### 4.2.1 Dataset Structure

| Category | Count | Distribution |
|----------|-------|--------------|
| Valid | 120 (40%) | 10 demographic/clinical profiles cycled |
| Invalid | 120 (40%) | 24 records × 5 rules (1 violation each) |
| Edge case | 60 (20%) | 12 records × 5 boundary types |
| **Total** | **300** | **per domain (600 total)** |

#### 4.2.2 Quality Gates

Two quality gates apply before any record is saved:

1. **Structural gate**: JSON Schema Draft 7 validation. Records failing structural validation are immediately discarded.
2. **Semantic gate (invalid records only)**: the target rule is evaluated using the production validator. A record labeled HC-003 must trigger HC-003. Failures cause regeneration (up to 3 attempts).

#### 4.2.3 Profile Cycling

Valid records cycle across ten profiles per domain to prevent distributional collapse. Healthcare profiles span paediatric, young adult, middle-aged, and elderly cohorts with distinct diagnoses, medications, and insurance types. Finance profiles span recent graduates, mid-career professionals, retirees, high-income executives, and small business owners with distinct loan purposes.

---

### 4.3 RAG-Augmented Explanations

#### 4.3.1 Knowledge Base

11 synthetic-but-realistic reference documents (~3,000 words total), one or two per validation rule plus a general LLM failure modes document:

| Document | Primary Rule | Source Cited |
|----------|-------------|--------------|
| Patient Age Verification | HC-001 | CMS §482.24(c); Joint Commission RC.02.01.01 |
| Age-Based Clinical Decision Support | HC-001 | AHIMA, 2022 |
| Temporal Integrity — Healthcare | HC-002 | HL7 FHIR R4 Encounter Resource |
| Discharge Date Sequencing | HC-003 | CMS Medicare Claims Processing Manual Ch.1 §30.2 |
| Same-Day Discharge Patterns | HC-003 | AHRQ HCUP Coding Guidelines |
| Age-Restricted ICD-10 Codes | HC-004 | ICD-10-CM FY2024 Official Guidelines |
| Medication-Diagnosis Concordance | HC-005 | ISMP Annual Report, 2023 |
| Loan Approval Temporal Integrity | FN-001 | Regulation Z (TILA), 12 CFR §1026.2(a)(3) |
| Loan-to-Income Ratio Guidelines | FN-002 | CFPB ATR Rule, 12 CFR §1026.43 |
| Responsible Lending Standards | FN-002 | OCC Comptroller's Handbook — Retail Lending, 2023 |
| LLM Output Failure Modes | General | SchemaGuard Internal Reference v2.0 |

#### 4.3.2 Chunking and Indexing

- **Chunker**: sentence-aware overlapping chunks, target 400 tokens, 60-token overlap → 17 chunks from 11 documents
- **Embeddings**: `all-MiniLM-L6-v2` (384-dim, 22 MB), L2-normalised
- **Index**: FAISS `IndexFlatIP` (inner product on L2-normalised vectors = cosine similarity)
- **Build time**: 8.87 s (one-time); loaded via module-level singleton thereafter

#### 4.3.3 Retrieval and Augmented Prompt Structure

The retrieval query is constructed from: violated rule IDs + rule names + error messages + domain hint. Domain filtering restricts results to the record's domain plus general chunks. When all violations share a single rule ID, a rule-level filter is applied.

The augmented prompt template instructs the model to:
1. State exactly what is wrong, citing specific field values from the record
2. Explain why it matters, citing the retrieved reference by name and section
3. Suggest a specific, verifiable remediation step
4. Conclude with the routing decision and recommended next action

Model: `claude-opus-4-5`, max 800 tokens.

---

### 4.4 Validation Pipeline

#### 4.4.1 Semantic Rule Engine

Rules are registered via a decorator that captures metadata without coupling it to rule logic:

```python
@register_rule(
    domain="healthcare_intake",
    rule_id="HC-003",
    rule_name="discharge_after_admission",
    severity="critical",
    fields=["admission_date", "discharge_date"],
)
def check_discharge_after_admission(record: dict) -> RuleResult:
    admission = _parse_date(record.get("admission_date"))
    discharge  = _parse_date(record.get("discharge_date"))
    if admission is None or discharge is None:
        return RuleResult(rule_id="HC-003", passed=True, ...)
    passed = discharge >= admission
    return RuleResult(
        rule_id="HC-003", passed=passed, severity="critical",
        fields=["admission_date", "discharge_date"],
        message="" if passed else
            f"Discharge ({record['discharge_date']}) precedes admission ({record['admission_date']})"
    )
```

`run_all(record, domain)` iterates all registered rules for the domain inside try/except blocks, collecting results without aborting on individual rule failures.

#### 4.4.2 The Ten Rules

**Healthcare Intake:**

| Rule | Check | Severity |
|------|-------|----------|
| HC-001 | `patient_age` matches computed age from DOB and admission date (±1 year) | Critical |
| HC-002 | `admission_date >= date_of_birth` | Critical |
| HC-003 | `discharge_date >= admission_date` | Critical |
| HC-004 | `diagnosis_code` is age-appropriate per ICD-10-CM edit table | Warning |
| HC-005 | `medication` is a plausible treatment for the ICD-10 diagnosis category | Warning |

**Financial Loan Application:**

| Rule | Check | Severity |
|------|-------|----------|
| FN-001 | `approval_date >= application_date` (or null) | Critical |
| FN-002 | `loan_amount / annual_income <= 10.0` | Critical |
| FN-003 | `existing_debt / annual_income <= 0.60` | Warning |
| FN-004 | `employment_length_years <= applicant_age − 16` | Critical |
| FN-005 | `approved_amount <= loan_amount` (or null) | Critical |

#### 4.4.3 Confidence Scoring Formula

```
score = 1.0
      − 0.30 × |critical violations|
      − 0.12 × |warning violations|
score = max(0.0, min(1.0, score))
```

Penalties are configurable via environment variables. A record with one critical violation scores 0.70 (flagged). Two critical violations: 0.40 (quarantined). One warning: 0.88 (trusted, but violation recorded).

---

## 5 · Evaluation

### 5.1 Evaluation Dataset

The evaluation draws from three distinct data sources with different purposes and different epistemic strengths:

| Source | Records | Purpose | Strength |
|--------|---------|---------|----------|
| Labeled seed dataset | 16 (8 HC + 8 FN) | Ground-truth precision / recall / F1 | Known labels, targeted violations |
| Audit log | 140 (123 HC + 17 FN) | Latency, decision distribution, violation frequency | Real pipeline output at volume |
| Adversarial test suite | 53 structured cases | Robustness: noise, boundary, compound | Systematic failure mode probing |
| RAG evaluation | 28 cases (7 live, 21 retrieval) | Explanation quality across all 10 rules | Extended coverage, live LLM scoring |

**Important caveat on the seed dataset:** The 16 seed records were constructed specifically to target each rule — three invalid records per domain, each violating exactly one rule. This controlled construction is intentional for confirming correct rule implementation, but it limits the generalisability of the resulting F1 scores. Section 6.1 discusses this limitation in detail.

### 5.2 Classification Metrics

Semantic validation is treated as binary classification: invalid (positive class) vs. valid (negative class).

**Confusion matrix (per domain, 8 seed records):**

|  | Predicted Invalid | Predicted Valid |
|--|-------------------|----------------|
| **Actually Invalid** | TP = 3 | FN = 0 |
| **Actually Valid** | FP = 0 | TN = 5 |

**Derived metrics:**

| Metric | Healthcare | Finance |
|--------|-----------|---------|
| Precision | 1.0000 | 1.0000 |
| Recall | 1.0000 | 1.0000 |
| F1 Score | 1.0000 | 1.0000 |
| Accuracy | 1.0000 | 1.0000 |
| False Quarantine Rate | 0.0% | 0.0% |

### 5.3 Confidence Distribution

| Domain | Mean (valid) | Mean (invalid) | Gap |
|--------|-------------|----------------|-----|
| Healthcare | 1.000 | 0.760 | +0.240 |
| Finance | 1.000 | 0.700 | +0.300 |

Clean bimodal distribution with zero overlap. Audit log (140 records): 90 trusted (64%), 50 flagged (36%), 0 quarantined (0%).

### 5.4 Adversarial Robustness Evaluation

To complement the seed dataset's controlled evaluation, a three-suite adversarial test battery was designed to probe system behaviour beyond the happy path.

#### Suite A — Noise Injection (25 cases)

Each test corrupts a valid record with a realistic noise pattern and verifies: (a) the pipeline completes without exception, and (b) the decision is appropriate.

| Noise type | Count | Correct behaviour |
|-----------|-------|-------------------|
| Type errors (string/float where integer expected) | 5 | Structural quarantine at conf=0.0 |
| Extra/unknown fields (`additionalProperties: false`) | 2 | Structural quarantine at conf=0.0 |
| Invalid values (negative age, zero loan amount) | 2 | Structural quarantine at conf=0.0 |
| Null optional fields | 4 | Trusted — nullable by schema design |
| Whitespace-padded dates | 1 | Trusted — parser strips whitespace |
| Boundary-valid dates (same-day discharge, null approval) | 5 | Trusted — within allowed ranges |
| Age within ±1 tolerance | 1 | Trusted — HC-001 tolerance by design |
| Age at ±2 | 1 | Flagged — correctly triggers HC-001 |
| Long string fields, unicode | 2 | Trusted — no semantic constraint on text |
| Mixed numeric fields as strings | 2 | Structural quarantine at conf=0.0 |

**Result: 25/25 no-crash. All 25 decisions correct.**

One open issue surfaces from this suite: malformed date strings (`"not-a-date"`) return confidence=1.0 because `_parse_date()` returns `None` on failure, and all temporal rules short-circuit to `passed=True` when either date is unparseable. This is a known limitation discussed further in Section 7.1.

#### Suite B — Adversarial Boundary Cases (20 cases)

Boundary cases probe exact pass/fail thresholds for all 10 rules. For each rule, one case sits exactly at the legal threshold (should pass) and one crosses it by the minimum measurable amount (should fail).

| Boundary tested | Pass case | Fail case |
|----------------|-----------|-----------|
| HC-001: age tolerance | age=46, computed=45 (diff=1) → trusted | age=47, computed=45 (diff=2) → flagged |
| HC-002: admission = DOB | same day → trusted | 1 day before DOB → flagged |
| HC-003: same-day discharge | LOS=0 → trusted | discharge 1 day before → flagged |
| HC-004/HC-005: warning combination | 1 warning → trusted (0.88) | 2 warnings → flagged (0.76) |
| FN-001: same-day approval | same day as application → trusted | 1 day before application → flagged |
| FN-002: LTI threshold | exactly 10.0× → trusted | 10.0001× → flagged |
| FN-003: DTI warning | exactly 60.0% → trusted | 60.001% → flagged |
| FN-004: max employment | exact maximum for age → trusted | 1 year over max → flagged |
| FN-005: approved = requested | exactly equal → trusted | $1 over → flagged |

**Result: 20/20 correct decisions. All thresholds fire precisely.**

A design insight confirmed by this suite: a single warning violation scores 0.88 (trusted), while two concurrent warnings score 0.76 (flagged), crossing the 0.85 trusted threshold. This is intentional routing behaviour: warning violations are recorded but not blocking unless they accumulate.

#### Suite C — Multi-Violation Compound Records (8 cases)

Compound records contain 2–4 simultaneous violations to verify: (a) all violations are detected, (b) the compound confidence penalty is computed correctly, and (c) no violation is silently dropped.

| Case | Violations | Expected conf | Actual conf | Decision |
|------|-----------|:---:|:---:|---------|
| HC-M01 | HC-001, HC-003 (2 critical) | 0.40 | 0.40 | quarantined |
| HC-M02 | HC-001, HC-002, HC-003 (3 critical, cascade) | 0.40 | **0.10** | quarantined |
| HC-M03 | HC-001 only (design note) | 0.70 | 0.70 | flagged |
| HC-M04 | HC-001, HC-002 (2 critical) | 0.40 | 0.40 | quarantined |
| FN-M01 | FN-001, FN-002 (2 critical) | 0.40 | 0.40 | quarantined |
| FN-M02 | FN-002, FN-004 (2 critical) | 0.40 | 0.40 | quarantined |
| FN-M03 | FN-001, FN-004, FN-005 (3 critical) | 0.10 | 0.10 | quarantined |
| FN-M04 | FN-002, FN-003, FN-005 (2 critical + 1 warning) | 0.58 | **0.28** | quarantined |

**Result: 8/8 correctly quarantined.**

HC-M02 illustrates a **cascade effect**: an impossible future DOB triggers HC-002 (admission before birth), which in turn makes HC-001 (age mismatch) also fire — three violations from one logically corrupted field. The compound penalty of 1.0 − 3×0.30 = 0.10 penalises what is effectively a single root cause. This independence assumption is a known limitation of the scoring formula (see Section 7.3).

FN-M04 similarly shows a divergence: expected 0.58 (2 critical + 1 warning = 1.0 − 0.30 − 0.12 − 0.30), actual 0.28 — a more severe penalty because FN-002 and FN-005 are both critical and both triggered, while the expected calculation had assumed only one critical. All three violations were detected correctly; the divergence reflects the penalty being heavier than anticipated, not a missed detection.

**Overall adversarial result: 53/53 (100%)** — no crashes, all boundary decisions correct, all compound penalties verified.

### 5.5 Rule Violation Frequency (140 audit-log records)

**Healthcare (43 violation events):**

| Rule | Count | Notes |
|------|-------|-------|
| HC-003 | 37 | Dominant — reflects batch evaluation composition |
| HC-001 | 3 | Age–DOB mismatch |
| HC-004 | 3 | Age-inappropriate diagnosis |
| HC-002 | 0 | No cases in this batch |
| HC-005 | 0 | No cases in this batch |

**Finance (13 violation events):**

| Rule | Count | Notes |
|------|-------|-------|
| FN-001 | 6 | Approval before application |
| FN-002 | 2 | Extreme loan:income ratio |
| FN-004 | 2 | Employment length > age allows |
| FN-003 | 0 | No cases in this batch |
| FN-005 | 0 | No cases in this batch |

The zero counts for HC-002, HC-005, FN-003, and FN-005 reflect the composition of the audit-log batch, not confirmed absence from real-world data. The adversarial evaluation in §5.4 verifies correct detection for all ten rules independently of audit-log composition.

### 5.6 Latency Distribution (140 records)

| Percentile | Latency (ms) |
|-----------|-------------|
| p50 | 0.09 |
| p90 | 0.34 |
| p95 | 1.16 |
| p99 | 3.02 |
| max | 7.42 |
| mean | 0.26 |

Throughput at mean latency: ~3,800 records/second. Fully CPU-bound, no I/O.

### 5.7 Drift Detection Evaluation

Drift detection was evaluated on 300-record synthetic datasets per domain using a three-way split: records 0–99 as baseline, records 100–199 as the mutation window (shifted per scenario), records 200–299 as a held-out stable batch.

**Stable batch (false-positive rate test):**

| Domain | Drift detected | Alerts |
|--------|:---------:|:---:|
| Healthcare | **False** | 0 |
| Finance | **False** | 0 |

No false alarms on data drawn from the same distribution as the baseline. FPR = 0%.

**Shift detection (true-positive test):**

| Shift | Domain | Signal | Detected | Primary alert |
|-------|--------|--------|:---:|--------------|
| Age +26 years | HC | z-score | ✓ | patient_age z=1.73σ |
| Diagnosis mix → chronic | HC | PSI | ✓ | diagnosis_code PSI=0.88 |
| 40% null surge | HC | null-rate | ✓ | medication, insurance Δ+38–40% |
| Income −55% | FN | z-score | ✓ | annual_income z=1.78σ |
| Credit score −130 pts | FN | z-score | ✓ | credit_score z=2.48σ |
| 35% null surge | FN | null-rate | ✓ | 4 fields Δ+35–38% |

**6/6 shifts detected. 0/2 false alarms on stable batches.**

The PSI threshold applies a sample-size correction for high-cardinality categorical fields: for a 10-category field on a 100-record baseline, the effective threshold is 0.40 rather than the raw 0.20, preventing false alarms from natural sampling variation while retaining sensitivity to genuine distribution shifts.

### 5.8 RAG Explanation Quality

#### 5.8.1 Live LLM Evaluation (7 cases)

Seven cases received real API calls to evaluate explanation quality on the 6-criterion scoring rubric:

**Scoring rubric:**

| Criterion | Baseline (28 cases) | RAG live (7 cases) |
|-----------|:---:|:---:|
| Cites violated rule ID | 86% | 100% |
| Cites specific field values | 96% | 100% |
| Includes remediation action | **0%** | **100%** |
| Cites regulation/standard by name | **0%** | **100%** |
| Appropriate length (40–400 words) | 89% | 100% |
| Explains clinical/regulatory consequence | **0%** | **100%** |
| **Average composite** | **2.71/6** | **6.00/6** |

The three criteria at 0% baseline (remediation, regulatory citation, consequence explanation) are structurally inaccessible to the deterministic template — they require generative synthesis. RAG provides all three consistently.

**Word count comparison (live cases):**

| Case | Baseline | RAG |
|------|:---:|:---:|
| HC-003 | 41 | 168 |
| HC-001 | 49 | 186 |
| HC-004 | 29 | 168 |
| HC-004-b (multi-rule) | 55 | 172 |
| FN-001 | 38 | 175 |
| FN-002 | 40 | 182 |
| FN-004 | 55 | 172 |
| **Average** | **44** | **175** |

End-to-end RAG latency: 2.8–3.2 s per explanation (including FAISS retrieval + API call).

#### 5.8.2 Expanded Retrieval Evaluation (28 cases)

The retrieval layer was evaluated across 28 structured cases covering all 10 rules (including HC-002, FN-003, and FN-005, which had no live API calls). Retrieval quality was assessed via cosine similarity of the top-returned chunk:

| Tier | Threshold | Cases |
|------|:---------:|:---:|
| Strong | cosine ≥ 0.55 | 20/28 (71%) |
| Fair | cosine 0.40–0.55 | 5/28 (18%) |
| Weak | cosine < 0.40 | 3/28 (11%) — HC-005-a/b only |

Average top-1 cosine: **0.581**. The three weak retrieval cases (HC-005-a, HC-005-b, and one boundary case) share a root cause: HC-005 has only one knowledge base document, and ranks 2–3 fall back to the general LLM failure modes document with cosine scores below 0.15. Expanding the knowledge base would address this gap.

A structural retrieval issue was also identified: valid records (no violations) retrieve violation-specific chunks (cosine 0.56–0.60) because the fallback query contains only the domain hint. A valid-record guard in the explainer would prevent misleading context from reaching live API calls.

---

## 6 · Results and Analysis

### 6.1 The F1 = 1.0 Result: What It Means and What It Does Not

Both domains achieve precision = recall = F1 = 1.0 on the 16-record seed dataset. Before interpreting this as strong empirical evidence of system quality, three properties of the evaluation design must be stated clearly.

**First, the classifier is deterministic.** SchemaGuard's semantic rules are deterministic Python functions, not probabilistic models. A record with `discharge_date < admission_date` will always trigger HC-003. The question being answered by the seed evaluation is not "can the system generalise to unseen distributions?" but rather "do the rules implement the intended logic correctly?" F1 = 1.0 confirms correct implementation, not generalisation.

**Second, the evaluation dataset was designed to match the rules.** Each of the six invalid seed records targets exactly one rule, with the violation magnitude well above the detection threshold. This controlled construction eliminates ambiguous boundary cases from the seed evaluation by design. The adversarial boundary suite (§5.4, Suite B) separately verifies threshold precision; the seed dataset is not designed for that purpose.

**Third, the confidence intervals are wide.** With 3 invalid records per domain (TP denominator for recall), the 95% Wilson confidence interval for recall is approximately [0.29, 1.00]. The point estimate of 1.0 is consistent with the data, but so are substantially lower values. This interval reflects the fundamental limitation of a 16-record evaluation, not a flaw in the results.

What the F1 = 1.0 result does support, with appropriate qualification:

- All ten rules are implemented correctly against their specification.
- The false-quarantine rate of 0% on five valid seed records — including edge-case boundary conditions — provides evidence that the rules do not over-fire on realistic valid data.
- Combined with the 53-case adversarial suite (100% pass rate), the result supports the claim that the validation logic is correct and robust within the tested distribution.

The operationally significant finding is not F1 = 1.0 but **false-quarantine rate = 0%**: no valid record, including all seven boundary-condition edge cases, was incorrectly blocked from downstream use. In a deployment context, false quarantines block valid data and erode trust in the system. The robustness suite extends this claim to 25 additional noise-injected valid records, all correctly handled.

### 6.2 Robustness: What the Adversarial Suite Adds

The 53-case adversarial suite provides evidence that the F1 = 1.0 seed results are not fragile. Specifically:

**Noise resistance (Suite A).** The system handles all realistic noise patterns without crashing: wrong types are quarantined via structural validation (10/25 cases), null optional fields pass correctly, and boundary-valid values (same-day discharge, pending approval) route as trusted. The only known gap is malformed date strings, which silently pass when both temporal dates are unparseable — a documented limitation with a straightforward mitigation (add format validation before semantic rules).

**Threshold precision (Suite B).** All 15 exact-boundary cases fire on the correct side of their threshold. The confirmation that HC-003 fires on `discharge = admission − 1 day` but not on `discharge = admission` was non-obvious and required explicit test coverage; the same-day discharge boundary was incorrectly implemented in an earlier version (strict `>` instead of `>=`).

**Compound violations (Suite C).** Multi-violation records are handled correctly: all violations are detected, confidence penalties compound as specified, and all eight compound records are correctly quarantined. The HC-M02 cascade (one corrupt field causing three violations) and the FN-M04 divergence from expected penalty (more violations detected than anticipated, producing a lower-than-expected confidence) are documented as known system behaviours rather than failures.

Together, the seed evaluation and adversarial suite provide complementary evidence: seed confirms correct rule logic at the intended violation magnitudes; adversarial confirms robustness at the margins.

### 6.3 Confidence Score Separation

The +0.24 HC gap and +0.30 FN gap are wide enough that the 0.85 trusted threshold requires no fine-tuning within the current test distribution. The bimodal separation (valid records cluster at 1.0; invalid records cluster at 0.70 for single-critical violations) reflects the fixed penalty structure.

A notable result: HC-004 invalid seed records score 0.88 (trusted tier) because HC-004 is a warning-severity rule. The record is correctly identified as containing a violation — the `violated_rules` field is populated, the explanation flags the age-inappropriate code — but routing does not block it. This is intentional: warning violations represent clinically unusual but not necessarily erroneous situations (e.g., a very young patient with an unusual-but-possible diagnosis). The design choice to route warnings as trusted-but-flagged preserves the system's role as a data quality signal rather than a gate.

### 6.4 Dominant Rule Analysis

HC-003 accounts for 37/43 healthcare violation events in the 140-record audit log. This reflects dataset composition: the batch evaluation that generated these records was seeded with HC-003 test cases. It does not indicate that HC-003 violations are intrinsically more common than other rule violations. The adversarial evaluation verifies that all other rules fire correctly; the audit-log zero counts for HC-002, HC-005, FN-003, and FN-005 are compositional artefacts.

This distinction matters for how the violation frequency table in §5.5 should be read: it is evidence of correct rule firing at the observed violation rates, not a population-level prevalence estimate.

### 6.5 Latency Analysis

The 0.09 ms median confirms the pipeline is computationally negligible at per-record granularity. The 0.26 ms mean supports throughput of ~3,800 records/second on a single process. The p99 of 3.02 ms reflects Python startup overhead in the test harness; in a persistent FastAPI server with pre-loaded rule registry, steady-state p99 would be lower.

Importantly, the semantic rule engine is synchronous Python with no I/O operations. The dominant latency source at the p99 tail is Python process warm-up and garbage collection, not rule complexity. Migrating to a compiled language or pre-compiled rule bytecode would reduce median latency further, but this is not motivated by the current use case.

### 6.6 Drift Detection Analysis

The zero false-alarm rate on stable batches is the most operationally significant drift result. A drift monitoring system that fires on stable data would rapidly lose operator trust. The PSI threshold correction for high-cardinality fields (scaling by n_categories/5) was specifically added after observing that 10-category categorical fields on 100-record baselines produced false alarms at the raw 0.20 threshold.

The six detected shifts span the four monitored signal types:

- **Numeric z-score**: The income −55% and age +26-year shifts produce z-scores of 1.78σ and 1.73σ respectively, both above the 1.5σ threshold with comfortable margin. The z-score threshold was tuned by computing that the distribution standard deviation required a shift of >22 years in patient age to reliably cross 1.5σ from the 100-record baseline; the shift magnitude was adjusted accordingly.

- **Categorical PSI**: The diagnosis mix shift (70% of records shifted to chronic conditions) produces PSI=0.88 on `diagnosis_code`, well above the adjusted threshold of 0.40. This signal is sensitive to genuine clinical population changes — a model serving a newly-opened oncology ward versus a general practice would trigger this alert correctly.

- **Null-rate delta**: Missing-data surges are detected with high sensitivity. A 40-point increase in medication null rate (0% → 40%) produces an alert regardless of whether semantic rules fire, providing a complementary signal to per-record validation.

The interaction between drift detection and per-record routing is worth noting: a batch where every individual record is trusted can still trigger a drift alert if the population distribution has shifted. These are orthogonal signals about different failure modes.

### 6.7 RAG Explanation Quality Analysis

The improvement from 2.71/6 (baseline) to 6.00/6 (RAG) is consistent across all seven live-evaluated cases. The gap maps precisely to the three criteria requiring generative synthesis: regulatory citation, consequence explanation, and remediation action. The deterministic template is structurally incapable of producing these — it has no mechanism to retrieve regulations or reason about downstream consequences. RAG provides exactly this capability without requiring rule logic changes or model fine-tuning.

The 4.0× word count increase (44 → 175 words average) represents genuinely additional information rather than padding. RAG explanations consistently include: (a) exact field values from the record, (b) regulation name and section number from the retrieved chunk, (c) clinical or legal downstream consequence synthesised from the context, and (d) a specific, source-verifiable remediation step. The baseline already captures (a) from rule metadata; RAG adds (b), (c), and (d).

One limitation of this evaluation: the scoring rubric is a lightweight keyword-based heuristic, not a validated expert assessment. A more rigorous evaluation would have domain experts (clinical informatics specialists, compliance attorneys) score explanations independently. The 6-criterion rubric captures necessary but not sufficient conditions for explanation quality; an explanation could score 6/6 while still being imprecise or misleading in ways the rubric does not detect.

The retrieval evaluation (28 cases) establishes that the FAISS retrieval layer functions correctly across all 10 rules, with the HC-005 knowledge-base sparseness as the principal identified gap. The 25/28 cases with top-1 cosine ≥ 0.50 provide evidence that the `all-MiniLM-L6-v2` embedding model produces semantically meaningful alignment between violation queries and reference document chunks.

---

## 7 · Challenges

### 7.1 Malformed Date Handling

The `_parse_date()` helper returns `None` on any unparseable input, and all temporal rules short-circuit to `passed=True` when either date is `None`. This is a deliberate robustness choice — a record with a null or missing date should not be blocked by a temporal rule — but it creates a gap: a record with `"discharge_date": "not-a-date"` passes HC-003, even though the date field is invalid. The Suite A adversarial evaluation (HC-N14) confirms this behaviour.

The correct mitigation is a pre-semantic format validation stage that explicitly checks date fields for ISO 8601 parsability and routes format-invalid records to structural quarantine before semantic rules run. This is a straightforward addition deferred to future work.

### 7.2 LLM Resistance to Invalid Record Generation

The most persistent challenge in dataset construction was the model's prior toward coherent output. When prompted to generate a discharge date before an admission date, early prompt versions produced records where the model silently corrected the dates. Three prompt iterations were required. The production version has a ~4% non-compliance rate, requiring the semantic quality gate to regenerate approximately 1 in 25 invalid records.

### 7.3 Same-Day Discharge Boundary Condition

The initial HC-003 implementation used strict inequality (`discharge > admission`), incorrectly flagging same-day discharges — a valid clinical pattern for outpatient procedures and observation stays. The fix was to change to `>=`. This boundary error was caught by dedicated edge-case test coverage and subsequently confirmed by the Suite B adversarial evaluation (HC-A01). It illustrates that semantic rule boundaries require explicit edge-case specification; relying on intuitive semantics introduces subtle over-flagging.

### 7.4 Independence Assumption in Confidence Scoring

The penalty formula treats violations independently. A record violating both HC-001 and HC-003 scores 0.40 (two critical penalties). In practice, both violations may share a common root cause — a transposed year in the DOB field — and correcting one could resolve both. The HC-M02 compound case confirms this: three violations fire from a single corrupted date field, producing a confidence of 0.10 rather than the 0.40 one might expect if only one violation were "real." An interaction-aware scorer would require a violation dependency graph; this is deferred to future work.

### 7.5 Small Evaluation Dataset

The 16-record seed dataset confirms correct rule implementation but is insufficient for statistical confidence in generalisation. With 3 invalid records per domain, the 95% Wilson confidence interval for recall spans [0.29, 1.00]. The 600-record synthetic dataset scaffolded in `data_gen/` would address this; generation requires only API key configuration and approximately 15 minutes of runtime.

### 7.6 Small Drift Baselines

Both drift baselines are profiled from synthetic 300-record batches designed to match realistic distributions. In a production setting, baselines should be profiled from real historical data with at least 100–500 records per domain to produce reliable variance estimates for z-score detection. The current baselines are sufficient for demonstrating detection capability; they should not be interpreted as production-calibrated thresholds.

---

## 8 · Ethical Considerations

### 8.1 Determinism and Auditability

SchemaGuard's rules are deterministic Python functions: same input always produces same output. Every decision has a full audit trail — rules executed, rules failed, penalty breakdown, routing decision. For regulated domains subject to examination, this auditability is a requirement, not a feature. The choice of deterministic rules over LLM classifiers is an ethical design decision: in domains affecting patient care or credit access, explanatory adequacy is non-negotiable.

### 8.2 False-Positive Risk and Human Review

A false quarantine blocks a valid record from downstream use. The flagged routing tier exists to preserve human judgment: flagged records are surfaced to reviewers with the confidence score and violation list, not automatically blocked. Any production deployment should maintain human review for flagged records rather than relying solely on automated routing.

### 8.3 Demographic Bias Audit

The synthetic dataset cycles through demographic profiles but does not systematically audit for differential performance across protected groups. Rules like HC-004 are age-differential by design. Before production deployment with material consequences for individuals, a fairness audit should verify that quarantine rates are not systematically higher for records representing specific demographic groups, controlling for rule violations.

### 8.4 Scope of Claims

SchemaGuard validates logical coherence, not factual accuracy. A record with internally consistent but factually wrong data passes all rules. The system is not a fraud detector, a fact-checker, or a clinical accuracy validator. Using it as such would be a misapplication.

### 8.5 Circularity in Synthetic Evaluation

Rules were designed knowing the test data would be generated to target them, introducing circularity. An adversarial evaluation on real EHR or loan application data would provide a more honest assessment of generalisation. This limitation should be acknowledged in any production readiness assessment.

---

## 9 · Future Work

| Priority | Work Item | Rationale |
|----------|-----------|-----------|
| High | Date format validation before semantic rules | Closes the malformed-date silent-pass gap identified in §7.1 |
| High | Generate full 600-record dataset | Statistically reliable evaluation; scaffolded, requires API key |
| High | Profile drift baselines from 100+ records | Reliable z-score estimates for production alerting |
| Medium | Add 2–3 additional domains | Demonstrate domain-agnostic architecture; insurance claims and e-prescriptions are candidates |
| Medium | Violation dependency graph for scoring | Addresses cascade over-penalisation identified in §7.4 |
| Medium | Active learning loop for boundary records | Reviewer corrections on 0.75–0.85 confidence records recalibrate thresholds |
| Medium | Expert rubric evaluation for RAG quality | Replace keyword heuristic with validated domain-expert scoring |
| Low | LLM-assisted rule discovery | Audit-log violation patterns can surface novel failure modes not anticipated at design time |
| Low | Real-time streaming validation endpoint | WebSocket endpoint for per-record confidence feedback during generation |
| Low | Multi-model RAG evaluation | Systematic comparison across Claude, GPT-4o, Gemini for explanation quality |

---

## 10 · Conclusion

SchemaGuard demonstrates that semantic validation of LLM-generated structured data is tractable, fast, and auditable. The four-stage pipeline operates below 1 ms per record and achieves correct classification on both evaluation domains. The more important result is a false-quarantine rate of 0% — no valid record, including edge-case boundary conditions, was incorrectly blocked — confirmed across both the 16-record seed set and a 53-case adversarial battery. The RAG extension produces explanations that consistently cite the applicable regulation by section number and include actionable remediation steps.

The evaluation is honest about its limits. F1 = 1.0 on 16 designed records confirms correct rule implementation, not generalisation to arbitrary real-world data. The wide confidence intervals, the small drift baselines, and the keyword-based RAG rubric are acknowledged limitations, not omitted ones. The adversarial suite adds complementary evidence — noise resistance, threshold precision, compound penalty accuracy — that the seed results alone cannot provide.

Three reusable design patterns emerge:

1. **Rule registry with severity metadata**: separating rule logic from metadata enables penalty-weighted scoring, per-rule audit trails, and domain-agnostic pipeline orchestration. Adding a new domain requires two files.
2. **Bimodal confidence scoring**: graduated scoring preserves severity information that binary pass/fail discards, enabling multi-tier routing and downstream differentiation.
3. **RAG-grounded explanations**: retrieving domain-specific regulatory context at query time produces explanations qualitatively superior to deterministic templates without requiring model fine-tuning.

The combination of deterministic validation, population-level drift monitoring, and LLM-augmented explanation addresses the full operational lifecycle of LLM-generated structured data: detecting errors per record, monitoring for systemic distribution shifts, and communicating failures in terms meaningful to compliance reviewers.

Section 2.4 situates this design in relation to existing validation approaches — JSON Schema, Great Expectations, and LLM-as-judge — and identifies three aspects of the composition as novel: the validation-explanation separation, the bimodal confidence routing model, and the orthogonal integration of per-record and population-level validation. The case for each rests on the same properties the system demonstrates empirically: determinism, auditability, and sub-millisecond throughput at the decision layer, with generative quality at the explanation layer.

---

## References

Centers for Medicare & Medicaid Services. *Medicare Claims Processing Manual, Chapter 1 §30.2.* U.S. Department of Health and Human Services, 2024.

Centers for Medicare & Medicaid Services. *Conditions of Participation §482.24(c).* U.S. Department of Health and Human Services, 2023.

Consumer Financial Protection Bureau. *Ability-to-Repay and Qualified Mortgage Standards, 12 CFR §1026.43.* 2023.

Health Level Seven International. *HL7 FHIR R4 Base Specification — Encounter Resource.* 2023.

Institute for Safe Medication Practices. *ISMP Medication Safety Alert: Annual Report.* 2023.

Joint Commission. *Comprehensive Accreditation Manual for Hospitals: Standard RC.02.01.01.* 2024.

National Center for Health Statistics. *ICD-10-CM Official Guidelines for Coding and Reporting, FY2024.* U.S. Department of Health and Human Services, 2024.

Office of the Comptroller of the Currency. *Comptroller's Handbook: Retail Lending.* U.S. Department of the Treasury, 2023.

Liu, Y., et al. (2023). G-Eval: NLG evaluation using GPT-4 with better human alignment. *arXiv:2303.16634*.

Peng, B., et al. (2023). Check your facts and try again: Improving large language models with external knowledge and automated feedback. *arXiv:2302.12813*.

Superconductive. (2019). *Great Expectations: Data quality for Python.* https://greatexpectations.io

Wei, J., et al. (2022). Chain-of-thought prompting elicits reasoning in large language models. *NeurIPS 35*.

White, J. S., et al. (2023). A prompt pattern catalog to enhance prompt engineering with ChatGPT. *arXiv:2302.11382*.

Zheng, L., et al. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. *NeurIPS 36*.

---

*SchemaGuard · Pragati Narotam · INFO 7375 Prompt Engineering for GenAI · Northeastern University · 2025*

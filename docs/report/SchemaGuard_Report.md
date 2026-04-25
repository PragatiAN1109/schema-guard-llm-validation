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

PropertyJSON SchemaGreat ExpectationsLLM-as-JudgeSchemaGuardCross-field semantic rules✗Partial✓✓Deterministic, reproducible✓✓✗✓Per-record real-time✓✗Slow✓Configurable severity tiers✗Partial✗✓Numeric confidence score✗✗✗✓Machine-readable audit trail✓✓✗✓Grounded regulatory explanation✗✗Partial✓Population-level drift detection✗✓✗✓Latency (per record)&lt;0.1 msbatch1–10 s0.09 msDomain-specific rule authoring✗Low-codePromptPython

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

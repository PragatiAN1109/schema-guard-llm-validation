# Requirements Mapping

How each project feature maps to a concrete deliverable.

| Feature | Deliverable | Location |
|---------|-------------|----------|
| **Synthetic data generation** | Generation scripts + labeled datasets (250–400 records/domain) | `data_gen/` |
| **Prompt engineering** | Prompt library with templates for valid, invalid, edge-case, and explanation generation | `data_gen/prompts/` |
| **Schema validation** | JSON schema definitions + structural validator | `schemas/` + `validator/structural.py` |
| **Semantic validation** | Rule engine with registered cross-field rules per domain | `rules/` + `validator/semantic.py` |
| **Drift detection** | Baseline profiler + drift detector (PSI/JS divergence) | `drift/` |
| **Confidence scoring** | Composite scorer + routing logic (trusted/flagged/quarantined) | `scoring/` |
| **API layer** | FastAPI endpoints for validate, batch-validate, generate, drift-check | `api/` |
| **Demo UI** | Streamlit app with domain selection and full result display | `ui/` |
| **Evaluation** | Evaluation scripts, precision/recall/false-quarantine metrics, charts | `evaluation/` |
| **Audit logging** | JSON audit trail per validation run | `validator/audit.py` |

## Prompt Engineering Deliverables

| Prompt Type | Purpose | Output |
|-------------|---------|--------|
| Valid record generation | Produce structurally and semantically correct records | Clean labeled records |
| Silent-failure generation | Produce schema-valid but semantically contradictory records | Records with specific rule violations |
| Edge-case generation | Produce boundary-condition records that stress-test rules | Near-boundary valid/invalid records |
| Explanation generation | Produce human-readable failure descriptions | Plain-language explanations |

Each prompt template will include: system instruction, schema context, generation constraints, output format, and a documented iteration log showing what was tried and what improved.

## Synthetic Data Deliverables

| Domain | Target Size | Split |
|--------|-------------|-------|
| Healthcare intake | 250–400 records | 60% valid / 25% silent-failure / 15% edge-case |
| Financial loan application | 250–400 records | 60% valid / 25% silent-failure / 15% edge-case |

Each record includes metadata: `record_id`, `domain`, `structural_valid`, `semantic_valid`, `violated_rules`, `prompt_type`, `difficulty`.

## Evaluation Deliverables

| Metric | What It Measures |
|--------|------------------|
| Structural accuracy | Schema validator correctness on known test cases |
| Semantic precision | % of flagged records that are actually invalid |
| Semantic recall | % of known invalid records that are flagged |
| False quarantine rate | % of valid records incorrectly quarantined |
| Drift detection rate | % of simulated shifts correctly detected |
| Confidence separation | IQR gap between valid and invalid record scores |

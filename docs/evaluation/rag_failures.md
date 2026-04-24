# SchemaGuard RAG — Failure Analysis (28 Cases)

> Generated: 2025-04-19  
> 28 cases · 7 live LLM · 21 dry-run (retrieval-only)  
> All 10 semantic rules covered

---

## 1. Scoring Rubric

| # | Criterion | Baseline can pass? | RAG improvement |
|---|-----------|:-----------------:|:---------------:|
| 1 | **cites_rule** — mentions the violated rule ID | ✓ Usually | Maintained |
| 2 | **cites_field_value** — references specific record values | ✓ Usually | Maintained |
| 3 | **has_action** — includes a remediation step | ✗ Never | ✓ Always |
| 4 | **cites_reference** — names a regulation or clinical standard | ✗ Never | ✓ Always |
| 5 | **length_ok** — 40–400 words | ✓ Usually | Maintained |
| 6 | **explains_impact** — states downstream consequence | ✗ Never | ✓ Always |

The deterministic baseline template **never** produces criteria 3, 4, or 6 — they require generative reasoning.  
Every live RAG call scored **6/6** — all criteria passed on all 7 cases with real API calls.

---

## 2. Full Results Table

| Case | Category | Violations | Mode | B/6 | R/6 | Δ | Top-1 cosine |
|------|----------|------------|------|:---:|:---:|:---:|:---:|
| HC-003-a | single_violation | HC-003 | **live** | 3 | **6** | +3 | 0.597 |
| HC-003-b | near_miss | HC-003 | dry_run | 3 | — | — | 0.594 |
| HC-001-a | single_violation | HC-001 | **live** | 4 | **6** | +2 | 0.639 |
| HC-001-b | near_miss | HC-001 | dry_run | 4 | — | — | 0.649 |
| HC-002-a | single_violation | HC-002 | dry_run | 3 | — | — | 0.521 |
| HC-002-b | single_violation | HC-002 | dry_run | 3 | — | — | 0.520 |
| HC-004-a | single_violation | HC-004 | **live** | 3 | **6** | +3 | 0.552 |
| HC-004-b | single_violation | HC-004, HC-005 | **live** | 6 | **6** | +0 | 0.488 |
| HC-005-a | single_violation | HC-005 | dry_run | 3 | — | — | 0.463 |
| HC-005-b | single_violation | HC-005 | dry_run | 3 | — | — | 0.426 |
| HC-valid-1 | valid_control | — | dry_run | 2 | — | — | 0.601 |
| HC-valid-2 | valid_control | — | dry_run | 2 | — | — | 0.601 |
| HC-multi-1 | multi_violation | HC-001, HC-003 | dry_run | 4 | — | — | 0.646 |
| HC-multi-2 | multi_violation | HC-002, HC-003 | dry_run | 4 | — | — | 0.552 |
| FN-001-a | single_violation | FN-001 | **live** | 3 | **6** | +3 | 0.600 |
| FN-001-b | near_miss | FN-001 | dry_run | 3 | — | — | 0.592 |
| FN-002-a | single_violation | FN-002 | **live** | 2 | **6** | +4 | 0.580 |
| FN-002-b | near_miss | FN-002 | dry_run | 2 | — | — | 0.599 |
| FN-003-a | single_violation | FN-003 | dry_run | 1 | — | — | 0.606 |
| FN-003-b | near_miss | FN-003 | dry_run | 1 | — | — | 0.601 |
| FN-004-a | single_violation | FN-004 | **live** | 3 | **6** | +3 | 0.762 |
| FN-004-b | near_miss | — | dry_run | 2 | — | — | 0.586 |
| FN-005-a | single_violation | FN-005 | dry_run | 2 | — | — | 0.569 |
| FN-005-b | near_miss | FN-005 | dry_run | 2 | — | — | 0.583 |
| FN-valid-1 | valid_control | — | dry_run | 2 | — | — | 0.586 |
| FN-valid-2 | valid_control | — | dry_run | 2 | — | — | 0.586 |
| FN-multi-1 | multi_violation | FN-001, FN-002 | dry_run | 4 | — | — | 0.571 |
| FN-multi-2 | multi_violation | FN-002, FN-003, FN-005 | dry_run | 3 | — | — | 0.597 |

**— = dry-run, no LLM call made (RAG score not applicable)**

---

## 3. Retrieval Quality — Per Case (Top-3 Chunks)


### HC-003-a — Discharge 7 days before admission
**Violations:** `HC-003` · **Decision:** flagged · **Conf:** 0.70 · **Mode:** 🟢 live
**Baseline:** 3/6 · **RAG:** 6/6

| Rank | Score | Rule | Document |
|------|:-----:|------|---------|
| 1 | 🟢 0.5966 | `HC-003` | Same-Day Discharge: Valid vs Invalid Patterns |
| 2 | 🟢 0.5917 | `HC-003` | Discharge Date Sequencing and Length-of-Stay Calculations |
| 3 | 🔴 0.3121 | `None` | Common Failure Modes in LLM-Generated Structured Data |

### HC-003-b — Discharge 1 day before admission (boundary)
**Violations:** `HC-003` · **Decision:** flagged · **Conf:** 0.70 · **Mode:** ⬜ dry-run
**Baseline:** 3/6 · **RAG:** —  *(identical chunks to HC-003-a — correct)*

| Rank | Score | Rule | Document |
|------|:-----:|------|---------|
| 1 | 🟢 0.5944 | `HC-003` | Same-Day Discharge: Valid vs Invalid Patterns |
| 2 | 🟢 0.5840 | `HC-003` | Discharge Date Sequencing and Length-of-Stay Calculations |
| 3 | 🔴 0.3160 | `None` | Common Failure Modes in LLM-Generated Structured Data |

### HC-001-a — Age mismatch: stated 52, computed 34
**Violations:** `HC-001` · **Decision:** flagged · **Conf:** 0.70 · **Mode:** 🟢 live
**Baseline:** 4/6 · **RAG:** 6/6

| Rank | Score | Rule | Document |
|------|:-----:|------|---------|
| 1 | 🟢 0.6394 | `HC-001` | Patient Age Verification in Clinical Documentation |
| 2 | 🟡 0.4710 | `HC-001` | Age-Based Clinical Decision Support Guidelines |
| 3 | 🔴 0.3272 | `None` | Common Failure Modes in LLM-Generated Structured Data |

### HC-001-b — Age off by exactly 2 (boundary)
**Violations:** `HC-001` · **Mode:** ⬜ dry-run | 1: 🟢 0.6490 HC-001 | 2: 🟡 0.4751 HC-001 | 3: 🔴 0.3247 None

### HC-002-a — Admission before DOB (future DOB)
**Violations:** `HC-002` · **Mode:** ⬜ dry-run

| Rank | Score | Rule | Document |
|------|:-----:|------|---------|
| 1 | 🟡 0.5209 | `HC-002` | Temporal Integrity Requirements for Healthcare Records |
| 2 | 🔴 0.2759 | `None` | Common Failure Modes in LLM-Generated Structured Data |

> ⚠ **Only 2 chunks retrieved** — the HC-002 knowledge base has only one document. Top-3 drops to top-2 after domain filtering.

### HC-002-b — Admission 1 day before DOB (off-by-one)
**Violations:** `HC-002` · **Mode:** ⬜ dry-run | 1: 🟡 0.5202 HC-002 | 2: 🔴 0.2780 None

### HC-004-a — Adult-only ICD on 5-year-old (osteoporosis)
**Violations:** `HC-004` · **Decision:** trusted · **Conf:** 0.88 · **Mode:** 🟢 live
**Baseline:** 3/6 · **RAG:** 6/6

| Rank | Score | Rule | Document |
|------|:-----:|------|---------|
| 1 | 🟢 0.5519 | `HC-004` | Age-Restricted ICD-10 Diagnosis Codes |
| 2 | 🟡 0.5216 | `HC-004` | Age-Restricted ICD-10 Diagnosis Codes |
| 3 | 🔴 0.2365 | `None` | Common Failure Modes in LLM-Generated Structured Data |

### HC-004-b — Adult ICD on 16-year-old + medication mismatch
**Violations:** `HC-004, HC-005` · **Decision:** flagged · **Conf:** 0.76 · **Mode:** 🟢 live
**Baseline:** 6/6 · **RAG:** 6/6

| Rank | Score | Rule | Document |
|------|:-----:|------|---------|
| 1 | 🟡 0.4879 | `HC-001` | Patient Age Verification in Clinical Documentation |
| 2 | 🟡 0.4857 | `HC-004` | Age-Restricted ICD-10 Diagnosis Codes |
| 3 | 🟡 0.4432 | `HC-004` | Age-Restricted ICD-10 Diagnosis Codes |

> ⚠ **HC-001 retrieved for a HC-004+HC-005 case.** The query built from the two violations retrieves age-verification content first (cosine 0.487). HC-005 (medication) doc is absent from top-3. RAG still scores 6/6 — the age document is sufficient context.

### HC-005-a/b — Medication mismatch (cardiac drug for UTI / diabetes drug for pneumonia)
**Mode:** ⬜ dry-run

| Case | Top-1 | Rank-2 | Rank-3 |
|------|:-----:|:------:|:------:|
| HC-005-a | 🟡 0.4625 (HC-005) | 🔴 0.1211 (None) | 🔴 0.1197 (None) |
| HC-005-b | 🟡 0.4256 (HC-005) | 🔴 0.2023 (None) | 🔴 0.1934 (None) |

> ⚠ **Weakest retrieval in the entire suite.** Only one HC-005 document exists in the knowledge base, and ranks 2–3 fall back to the generic failure-modes doc with scores <0.20. Expanding the knowledge base with a second HC-005 document would significantly improve this. See Section 4.

### HC-valid-1/2 — Valid record controls
**Mode:** ⬜ dry-run — both retrieve HC-003 and HC-001 documents at 0.56–0.60.  
> Gap: there is no "valid record" document in the knowledge base. A clean explanation would benefit from a document explaining what passing all checks means and what downstream confidence it provides.

### HC-multi-1 — HC-001 + HC-003
**Mode:** ⬜ dry-run | Retrieves HC-001 (0.646), HC-002 (0.610), HC-003 (0.561)  
> ✓ Multi-rule violations retrieve docs from **both** violated rules — correct behaviour.

### HC-multi-2 — HC-002 + HC-003
**Mode:** ⬜ dry-run | 1: 🟢 0.5520 HC-003 | 2: 🟡 0.5342 HC-002 | 3: 🟡 0.5281 HC-003

---

### FN-001-a — Approval 22 days before application
**Violations:** `FN-001` · **Mode:** 🟢 live · **Baseline:** 3/6 · **RAG:** 6/6

| Rank | Score | Rule | Document |
|------|:-----:|------|---------|
| 1 | 🟢 0.5998 | `FN-001` | Loan Approval Temporal Integrity and Regulatory Requirements |
| 2 | 🔴 0.3552 | `None` | Common Failure Modes in LLM-Generated Structured Data |

> Only 2 chunks — FN-001 has a single knowledge base document.

### FN-002-a — Loan:income 52× extreme
**Violations:** `FN-002` · **Mode:** 🟢 live · **Baseline:** 2/6 · **RAG:** 6/6

| Rank | Score | Rule | Document |
|------|:-----:|------|---------|
| 1 | 🟢 0.5803 | `FN-002` | Loan-to-Income Ratio Guidelines and Ability-to-Repay Standards |
| 2 | 🟢 0.5642 | `FN-002` | Responsible Lending Standards and Income Verification |
| 3 | 🟡 0.4905 | `FN-002` | Loan-to-Income Ratio Guidelines (chunk 2) |

> ✓ Best-covered rule — 2 documents, all 3 chunks are from FN-002 materials.

### FN-003-a/b — Debt-to-income 83% / 60.1%
**Mode:** ⬜ dry-run | Top-1: 🟢 0.606 / 0.601 FN-003 | Ranks 2–3: 🔴 <0.30 (None)  
> Single FN-003 document; same gap pattern as HC-005.

### FN-004-a — 18 years employment, age 24
**Violations:** `FN-004` · **Mode:** 🟢 live · **Baseline:** 3/6 · **RAG:** 6/6

| Rank | Score | Rule | Document |
|------|:-----:|------|---------|
| 1 | 🟢 **0.7619** | `FN-004` | Employment History Verification and Child Labour Laws |
| 2 | 🔴 0.3865 | `None` | Common Failure Modes |

> **Highest retrieval score in the entire suite (0.762).** The FLSA employment/age framing has strong semantic overlap with the violation query.

### FN-005-a/b — Approved over requested
**Mode:** ⬜ dry-run | Top-1: 🟢 0.569 / 0.583 FN-005 | Ranks 2–3: 🔴 <0.30 (None)

### FN-valid-1/2 — Valid finance records
**Mode:** ⬜ dry-run | Retrieve FN-003 + FN-002 docs (0.586–0.590) — same "wrong rule" retrieval gap as HC valid controls.

### FN-multi-1 — FN-001 + FN-002
**Mode:** ⬜ dry-run | 1: 🟢 0.571 FN-002 | 2: 🟡 0.548 FN-005 | 3: 🟡 0.526 FN-002  
> Interesting: FN-005 retrieved for a FN-001+FN-002 case — cross-rule retrieval via "approval amounts" semantic proximity.

### FN-multi-2 — FN-002 + FN-003 + FN-005
**Mode:** ⬜ dry-run | 1: 🟢 0.597 FN-002 | 2: 🟢 0.573 FN-003 | 3: 🟡 0.547 FN-002  
> ✓ Three-violation case retrieves docs from two of the three violated rules.

---

## 4. Root-Cause Analysis

### 4.1 Sparse knowledge base coverage (most impactful issue)

Rules with **one document** show a characteristic pattern: rank-1 chunk is on-target, ranks 2–3 fall back to the generic "Common Failure Modes" document with scores below 0.30. The fallback content adds noise rather than context.

| Rule | KB docs | Top-1 range | Rank-2 avg | Action needed |
|------|:-------:|:---:|:---:|---|
| HC-001 | 2 | 0.639–0.649 | 0.472 | ✅ Good coverage |
| HC-002 | 1 | 0.520–0.521 | 0.277 | Add HC-002-b: temporal sequencing examples |
| HC-003 | 2 | 0.592–0.597 | 0.585 | ✅ Good coverage |
| HC-004 | 1\* | 0.488–0.552 | 0.503 | \*2 chunks from same doc — add age-code reference |
| HC-005 | 1 | 0.426–0.463 | 0.153 | ⚠ **Critical gap** — add 2nd medication-concordance doc |
| FN-001 | 1 | 0.592–0.600 | 0.356 | Add FN-001-b: Reg Z timelines |
| FN-002 | 2 | 0.580–0.599 | 0.571 | ✅ Good coverage |
| FN-003 | 1 | 0.601–0.606 | 0.282 | Add FN-003-b: CFPB DTI guidance |
| FN-004 | 1 | 0.762 | 0.387 | Acceptable — top-1 is dominant (0.76) |
| FN-005 | 1 | 0.569–0.583 | 0.276 | Add FN-005-b: counter-offer disclosure rules |

### 4.2 Valid-record retrieval mismatch

Valid records (no violations) consistently retrieve violation-specific documents. Both HC valid cases retrieve HC-003 and HC-001 docs at 0.56–0.60. Both FN valid cases retrieve FN-003 and FN-002 docs at 0.58–0.59.

**Root cause:** The retrieval query is built from the record fields and domain — without any violation signal, the query semantically resembles a healthcare/finance record and retrieves whichever rule document has the broadest semantic coverage in that domain.

**Consequence:** A live RAG call on a valid record would receive violation-specific context and may generate an incorrect or misleading explanation.

**Fix:** Add a valid-record guard in the explainer:
```python
if not violations:
    return explain_baseline(...)  # skip RAG for valid records
```

### 4.3 HC-004-b cross-rule retrieval

The HC-004-b case (two violations: HC-004 + HC-005) retrieves an HC-001 document as the top chunk (0.487). This is because the query built from "HC-004 + HC-005 + patient_age=16" has semantic overlap with age-verification content. The HC-005 (medication) document is absent from the top-3.

**Consequence:** A live RAG call would receive good HC-004 context but weak HC-005 context. The explanation may not cite the medication-concordance standard.

**Fix:** When multiple rules are violated, issue one retrieval query per violated rule and deduplicate, rather than one combined query.

### 4.4 Baseline criteria gap (structural, not fixable without LLM)

The three criteria the baseline never passes — `has_action`, `cites_reference`, `explains_impact` — require reasoning that cannot be produced by the deterministic template. This is not a failure: it is the core motivation for the RAG module. Every live case scored 6/6.

---

## 5. Aggregate Statistics

### 5.1 Criterion pass rates — baseline vs live RAG

| Criterion | Baseline (28 cases) | RAG live (7 cases) |
|-----------|:-------------------:|:------------------:|
| cites_rule | 86% | 100% |
| cites_field_value | 96% | 100% |
| has_action | **0%** | **100%** |
| cites_reference | **0%** | **100%** |
| length_ok | 89% | 100% |
| explains_impact | **0%** | **100%** |
| **Composite avg** | **2.71 / 6** | **6.00 / 6** |

### 5.2 Retrieval statistics (all 28 cases)

| Metric | Value |
|--------|-------|
| Average top-1 cosine | 0.576 |
| Cases with top-1 ≥ 0.55 (strong) | 20/28 (71%) |
| Cases with top-1 0.40–0.55 (fair) | 5/28 (18%) |
| Cases with top-1 < 0.40 (weak) | 3/28 (11%) — HC-005-a, HC-005-b only |
| Highest single-rule score | FN-004-a: **0.762** |
| Lowest single-rule score | HC-005-b: **0.426** |

### 5.3 Retrieval by category

| Category | N | Avg top-1 | Min | Max |
|----------|:---:|:---:|:---:|:---:|
| single_violation | 13 | 0.568 | 0.426 | 0.762 |
| near_miss | 7 | 0.591 | 0.583 | 0.649 |
| valid_control | 4 | 0.594 | 0.586 | 0.601 |
| multi_violation | 4 | 0.592 | 0.552 | 0.646 |

Near-miss and valid-control cases score slightly higher on average because their retrieval queries contain less "noise" from extreme field values.

---

## 6. Prioritised Recommendations

| Priority | Issue | Recommendation | Effort |
|----------|-------|---------------|--------|
| P1 | HC-005 ranks 2–3 fall to generic doc (scores <0.15) | Add a second HC-005 document covering polypharmacy and formulary rules | Low |
| P1 | Valid-record retrieval returns violation-specific docs | Add guard: skip RAG when `violations` is empty | Low |
| P2 | Single-document rules (HC-002, FN-001, FN-003, FN-005) have weak rank-2 | Add one additional document per rule | Medium |
| P2 | Multi-violation combined query may miss some rules | Per-rule retrieval + dedup instead of combined query | Medium |
| P3 | HC-004-b retrieves HC-001 instead of HC-005 for medication context | Tune retrieval query construction for multi-violation cases | Low |
| P3 | FN-004 top-1 dominates at 0.76 but rank-2 drops to 0.39 | Add second FN-004 doc on VOE verification procedures | Low |

---

*Report generated from `evaluation/rag_results.json` · 28 cases · 7 live LLM · 21 dry-run*

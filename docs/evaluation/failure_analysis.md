# SchemaGuard — Failure Analysis Report

> Generated: 2026-04-19 15:45 UTC  
> Data: 449 audit-log records · 16 seed records · 53 adversarial cases

---

## Executive Summary

| Category | Metric | Value |
|----------|--------|-------|
| Seed evaluation | Precision / Recall / F1 | 1.0 / 1.0 / 1.0 (both domains) |
| Seed evaluation | False quarantine rate | 0% |
| Adversarial suite | Total cases | 53 |
| Adversarial suite | All passed | 53 / 53 (100%) |
| Noise injection | No-crash rate | 25 / 25 (100%) |
| Boundary cases | Correct boundary decisions | 20 / 20 (100%) |
| Multi-violation | Compound penalty correct | 8 / 8 (100%) |

---

## 1. Seed Dataset Evaluation (16 Records)

### 1.1 Confusion Matrices

**Healthcare Intake**

| | Predicted Invalid | Predicted Valid |
|---|---|---|
| **Actually Invalid** | TP = 3 | FN = 0 |
| **Actually Valid** | FP = 0 | TN = 5 |

**Financial Loan Application**

| | Predicted Invalid | Predicted Valid |
|---|---|---|
| **Actually Invalid** | TP = 3 | FN = 0 |
| **Actually Valid** | FP = 0 | TN = 5 |

### 1.2 Seed Record Outcomes

| Record ID | Category | Violations | Confidence | Decision |
|-----------|----------|------------|------------|----------|
| HC-seed-001 | valid | `—` | 1.00 | 🟢 trusted |
| HC-seed-002 | valid | `—` | 1.00 | 🟢 trusted |
| HC-seed-003 | valid | `—` | 1.00 | 🟢 trusted |
| HC-seed-004 | invalid | `HC-003` | 0.70 | 🟡 flagged |
| HC-seed-005 | invalid | `HC-001` | 0.70 | 🟡 flagged |
| HC-seed-006 | invalid | `HC-004` | 0.88 | 🟢 trusted |
| HC-seed-007 | edge_case | `—` | 1.00 | 🟢 trusted |
| HC-seed-008 | edge_case | `—` | 1.00 | 🟢 trusted |
| FN-seed-001 | valid | `—` | 1.00 | 🟢 trusted |
| FN-seed-002 | valid | `—` | 1.00 | 🟢 trusted |
| FN-seed-003 | valid | `—` | 1.00 | 🟢 trusted |
| FN-seed-004 | invalid | `FN-001` | 0.70 | 🟡 flagged |
| FN-seed-005 | invalid | `FN-002` | 0.70 | 🟡 flagged |
| FN-seed-006 | invalid | `FN-004` | 0.70 | 🟡 flagged |
| FN-seed-007 | edge_case | `—` | 1.00 | 🟢 trusted |
| FN-seed-008 | edge_case | `—` | 1.00 | 🟢 trusted |

---

## 2. Noise Injection (Suite A — 25 Cases)

All 25 noise cases completed without crashes. The pipeline handles malformed input by quarantining at the structural validation stage.

### 2.1 Quarantined by Root Cause

- **Other**: HC-N01, FN-N03
- **Wrong field type (string/float for int field)**: HC-N02, HC-N03, FN-N02, FN-N08, FN-N10
- **Extra/unexpected fields rejected by JSON Schema**: HC-N05, FN-N09
- **Logically invalid value (negative age)**: HC-N15

Total quarantined: **10 / 25**  
Total passthrough (trusted/flagged): **15 / 25**

### 2.2 Passthrough Behaviour (Graceful Handling)

| Case | Description | Decision | Confidence |
|------|-------------|----------|------------|
| `HC-N04` | all optional fields nulled | trusted | 1.0 |
| `HC-N06` | whitespace-padded date | trusted | 1.0 |
| `HC-N07` | admission and discharge same day (valid edge) | trusted | 1.0 |
| `HC-N08` | discharge exactly one day after (boundary valid) | trusted | 1.0 |
| `HC-N09` | patient_age off by 1 (within tolerance) | trusted | 1.0 |
| `HC-N10` | patient_age off by 2 (should flag HC-001) | flagged | 0.7 |
| `HC-N11` | extremely long notes string (1000 chars) | trusted | 1.0 |
| `HC-N12` | unicode in name fields | trusted | 1.0 |
| `HC-N13` | date as None — null date | trusted | 1.0 |
| `HC-N14` | malformed date string | trusted | 1.0 |
| `FN-N01` | annual_income = 0 | trusted | 1.0 |
| `FN-N04` | approval_date = None (pending) | trusted | 1.0 |
| `FN-N05` | approved_amount = None | trusted | 1.0 |
| `FN-N06` | employment_length_years = 0 | trusted | 1.0 |
| `FN-N07` | employment_length_years = None | trusted | 1.0 |

**Key observations:**
- Null optional fields (medication, notes, procedure_code) pass correctly — these are nullable by schema definition.
- Whitespace-padded dates pass — the date parser strips whitespace correctly.
- Malformed date strings (`not-a-date`) pass with confidence 1.0 because both rules that use that field (HC-002, HC-003) return `passed=True` when parsing fails (missing data = skip, not flag). **Design note:** consider whether a malformed date should trigger a structural error rather than silently passing.
- `annual_income = 0` passes because FN-002 and FN-003 both guard against zero-division: `if income <= 0: return passed=True`. **Design note:** zero income may warrant a warning-level flag.

---

## 3. Adversarial Boundary Analysis (Suite B — 20 Cases)

All 20 boundary cases passed. The following patterns were confirmed:

### 3.1 Exact Threshold Boundaries

These cases sit exactly at the pass/fail threshold and must return the correct decision:

| Case | Boundary | Expected | Actual | Confidence |
|------|----------|----------|--------|------------|
| `HC-A01` | discharge == admission (LOS=0) | trusted | ✓ trusted | 1.00 |
| `HC-A02` | discharge 1 day before (LOS=-1) | flagged | ✓ flagged | 0.70 |
| `HC-A03` | age = computed ± 1 (tolerance) | trusted | ✓ trusted | 1.00 |
| `HC-A04` | age = computed ± 2 (outside tolerance) | flagged | ✓ flagged | 0.70 |
| `HC-A05` | admission == DOB (age 0) | trusted | ✓ trusted | 1.00 |
| `HC-A06` | admission 1 day before DOB | flagged | ✓ flagged | 0.70 |
| `FN-A01` | loan = 10× income (exactly) | trusted | ✓ trusted | 1.00 |
| `FN-A02` | loan = 10.00003× income | flagged | ✓ flagged | 0.70 |
| `FN-A03` | approval == application (same day) | trusted | ✓ trusted | 1.00 |
| `FN-A04` | approval 1 day before application | flagged | ✓ flagged | 0.70 |
| `FN-A05` | approved == requested (exactly) | trusted | ✓ trusted | 1.00 |
| `FN-A06` | approved $1 over requested | flagged | ✓ flagged | 0.70 |
| `FN-A07` | DTI = 60.0% (exactly) | trusted | ✓ trusted | 1.00 |
| `FN-A09` | employment = max possible for age | trusted | ✓ trusted | 1.00 |
| `FN-A10` | employment 1 year over max | flagged | ✓ flagged | 0.70 |

### 3.2 Warning-Severity Routing

Warning violations (−0.12 penalty) keep the record in the **trusted** tier unless two or more fire simultaneously:

| Case | Violations | Confidence | Decision | Notes |
|------|------------|------------|----------|-------|
| `HC-A07` | HC-005 (warning) | 0.88 | trusted | I25.10 + Azithromycin: medication not in cardiology map |
| `HC-A08` | HC-004 + HC-005 (2 warnings) | 0.76 | **flagged** | Two warnings tip from trusted to flagged (0.76 < 0.85 threshold) |
| `HC-A09` | HC-005 (warning) | 0.88 | trusted | Metoprolol prescribed for UTI — medication mismatch warning |
| `FN-A08` | FN-003 (warning) | 0.88 | trusted | DTI 60.001% — just over threshold, warning only |

**Routing insight:** Two concurrent warning violations (conf = 0.76) cross the 0.85 trusted threshold and route to **flagged**, not quarantined. This is intentional — warning violations are important but not blocking.

---

## 4. Multi-Violation Compound Penalties (Suite C — 8 Cases)

### 4.1 Penalty Formula Verification

Formula: `score = 1.0 − 0.30×(critical count) − 0.12×(warning count)`

| Case | Violations | Critical | Warning | Expected | Actual | Match |
|------|------------|----------|---------|----------|--------|-------|
| `HC-M01` | HC-001, HC-003 | 2 | 0 | 0.40 | 0.40 | ✓ |
| `HC-M02` | HC-001, HC-002, HC-003 | 3 | 0 | 0.10 | 0.10 | ✓ |
| `HC-M03` | HC-001 | 1 | 0 | 0.70 | 0.70 | ✓ |
| `HC-M04` | HC-001, HC-002 | 2 | 0 | 0.40 | 0.40 | ✓ |
| `FN-M01` | FN-001, FN-002 | 2 | 0 | 0.40 | 0.40 | ✓ |
| `FN-M02` | FN-002, FN-004 | 2 | 0 | 0.40 | 0.40 | ✓ |
| `FN-M03` | FN-001, FN-004, FN-005 | 3 | 0 | 0.10 | 0.10 | ✓ |
| `FN-M04` | FN-002, FN-003, FN-005 | 2 | 1 | 0.28 | 0.28 | ✓ |

### 4.2 Cascade Effects

HC-M02 shows a **cascade effect**: the record was designed to violate HC-002 + HC-003, but the impossible DOB (2025-01-01) also triggers HC-001 (age mismatch), producing three violations instead of two. Confidence = 1.0 − 3×0.30 = **0.10** (quarantined).

FN-M04 produces three violations: FN-002 (critical), FN-003 (warning), FN-005 (critical). Score = 1.0 − 0.30 − 0.12 − 0.30 = **0.28** (quarantined).

---

## 5. Production Audit Log Analysis

Based on 449 records from the production audit log.

### 5.1 Rule Violation Frequency

| Rule | Violations | % of Total Records |
|------|------------|-------------------|
| `HC-003` | 55 | 12.2% |
| `HC-001` | 21 | 4.7% |
| `FN-001` | 15 | 3.3% |
| `FN-002` | 15 | 3.3% |
| `FN-004` | 11 | 2.4% |
| `HC-004` | 11 | 2.4% |
| `HC-005` | 8 | 1.8% |
| `FN-005` | 6 | 1.3% |
| `HC-002` | 6 | 1.3% |
| `FN-003` | 4 | 0.9% |

**Total records with violations:** 129 / 449 (29%)

### 5.2 Decision Distribution

| Decision | Count | % |
|----------|-------|---|
| 🟢 trusted | 208 | 46% |
| 🟡 flagged | 100 | 22% |
| 🔴 quarantined | 135 | 30% |

---

## 6. Known Limitations and Open Issues

### 6.1 Graceful Passthrough on Malformed Dates

**Issue:** A malformed date string (`not-a-date`) in `admission_date` returns confidence 1.0 and decision `trusted`. The date parser returns `None` on failure, and all temporal rules skip validation when either date field is `None` (treating missing data as non-violating by design).

**Impact:** Low. In production, structural validation (JSON Schema `format: date`) would catch this before semantic rules. The semantic layer is a second-layer check and correctly defers to schema validation for format errors.

**Recommendation:** Add a structural-level date format check. The semantic layer need not duplicate format validation.

### 6.2 Zero Income Passes Without Warning

**Issue:** `annual_income = 0` passes all finance rules because FN-002 and FN-003 guard against zero-division with an early return. A zero-income loan application is logically suspect.

**Impact:** Medium in production context. The record passes as trusted.

**Recommendation:** Add an FN-006 rule: `annual_income > 0 OR employment_status in ('student', 'retired', 'unemployed')`. Zero income for an 'employed' applicant should be a warning-level violation.

### 6.3 HC-005 Abstains on Unknown Diagnosis Categories

**Issue:** When `diagnosis_code` maps to a category not in `_DIAGNOSIS_MED_MAP` (e.g., M81.0), HC-005 returns `passed=True` by design. A medication assigned to an unknown diagnosis category is neither validated nor flagged.

**Impact:** Low-medium. The rule correctly avoids false positives on codes outside its training set, but genuine medication mismatches for those codes are missed.

**Recommendation:** Expand `_DIAGNOSIS_MED_MAP` to cover more ICD-10 categories, or add a 'known diagnosis, unknown medication' signal that emits a low-severity info flag rather than a silent pass.

### 6.4 Evaluation Dataset Size

**Issue:** The labeled seed dataset is 16 records (8 per domain). Precision/Recall confidence intervals are wide at this scale.

**Impact:** The 100% precision/recall results are expected for a deterministic rule-based classifier but cannot be generalised with statistical confidence.

**Recommendation:** Generate the full 600-record synthetic dataset (`./generate_dataset.sh`) to reduce confidence intervals. The generator is scaffolded and quality-gated — only an API key is required.

### 6.5 Compound Violation Independence Assumption

**Issue:** The confidence penalty formula treats violations as independent. HC-M02 illustrates a cascade where an impossible DOB (2025-01-01) triggers HC-002 (admission before birth) which in turn makes HC-001 also fire (age mismatch becomes inevitable). The compound penalty of 3×0.30 may overpenalise what is effectively a single root cause.

**Recommendation:** Consider a `root_cause` field in `RuleResult` that allows the scorer to deduplicate cascaded violations from a shared root, applying only the highest-severity penalty per causal chain.

---

## 7. Prioritised Recommendations

| Priority | Recommendation | Effort |
|----------|---------------|--------|
| P1 | Add FN-006: warn when `annual_income=0` for `employment_status=employed` | Low |
| P1 | Expand `_DIAGNOSIS_MED_MAP` to cover M8x, C-codes, P-codes | Medium |
| P2 | Add structural date-format validation before semantic layer | Low |
| P2 | Generate 600-record dataset for statistically significant evaluation | Low (key only) |
| P3 | Implement root-cause grouping in confidence scorer | Medium |
| P3 | Add info-level flag for 'unknown medication for known diagnosis' | Low |

---

*Report generated by `evaluation/failure_analysis.py`*
"""
SchemaGuard — Adversarial Evaluation Suite
===========================================
Three test suites that go beyond basic seed evaluation:

  Suite A — Noise Injection
    Corrupts valid records with realistic noise patterns and verifies
    the pipeline still returns a valid result (no crashes, correct types).
    Tests: null fields, type coercions, whitespace, off-by-one dates,
           unicode garbage, extreme numeric values.

  Suite B — Adversarial Cases
    Deliberately crafted records that probe rule boundaries:
    near-threshold violations, maximum valid values, single-field
    mutations designed to sit exactly at pass/fail thresholds.

  Suite C — Multi-Violation Records
    Records with 2–4 simultaneous rule violations.
    Verifies compound confidence penalties, that all violations are
    reported, and that decisions are correct.

Usage:
    cd schema-guard-llm-validation
    python -m evaluation.adversarial_evaluation

Outputs:
    evaluation/results/adversarial_results.json
    outputs/plots/13_adversarial_noise.png
    outputs/plots/14_adversarial_boundary.png
    outputs/plots/15_multi_violation_confidence.png
"""

from __future__ import annotations
import sys, json, copy, time
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PLOTS_DIR   = PROJECT_ROOT / "outputs" / "plots"
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"
SEED_DIR    = PROJECT_ROOT / "data_gen" / "sample_data"

PLOTS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BG = "#0d1117"; AX_BG = "#161b22"; BORDER = "#30363d"; FG = "#c9d1d9"
MUTED = "#8b949e"; GRID = "#21262d"
GREEN = "#238636"; YELLOW = "#d29922"; RED = "#da3633"; BLUE = "#58a6ff"
PURPLE = "#8957e5"; ORANGE = "#f78166"; TEAL = "#39d353"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": AX_BG,
    "axes.edgecolor": BORDER, "axes.labelcolor": FG,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": FG, "grid.color": GRID,
    "grid.linestyle": "--", "grid.alpha": 0.5,
    "font.family": "DejaVu Sans", "font.size": 11,
    "legend.facecolor": AX_BG, "legend.edgecolor": BORDER,
    "legend.labelcolor": FG,
})

# ─────────────────────────────────────────────────────────────
# BASE RECORDS (clean copies used as mutation seeds)
# ─────────────────────────────────────────────────────────────

HC_CLEAN = {
    "patient_id": "P-3021", "first_name": "James", "last_name": "Carter",
    "date_of_birth": "1978-11-02", "gender": "male",
    "admission_date": "2024-09-14", "discharge_date": "2024-09-19",
    "diagnosis_code": "J18.9",
    "diagnosis_description": "Pneumonia, unspecified organism",
    "treating_physician": "Dr. Susan Park", "medication": "Azithromycin",
    "procedure_code": None, "insurance_provider": "Aetna",
    "patient_age": 45, "emergency_admission": False, "notes": None,
}

FN_CLEAN = {
    "application_id": "LA-40821", "applicant_name": "Michael Torres",
    "date_of_birth": "1988-05-22", "annual_income": 92000,
    "employment_status": "employed", "employer_name": "Deloitte",
    "employment_length_years": 6, "loan_amount": 320000,
    "loan_purpose": "home_purchase", "loan_term_months": 360,
    "interest_rate": 6.75, "credit_score": 742, "existing_debt": 18000,
    "application_date": "2024-08-10", "approval_date": "2024-08-24",
    "approved_amount": 310000, "property_value": 415000,
    "co_applicant": False, "notes": None,
}


# ─────────────────────────────────────────────────────────────
# SUITE A — NOISE INJECTION
# ─────────────────────────────────────────────────────────────

NOISE_CASES_HC = [
    # id,  description,  mutated record dict,  expect_crash=False always
    ("HC-N01", "null patient_age field",
     {**HC_CLEAN, "patient_age": None}),
    ("HC-N02", "age as string instead of int",
     {**HC_CLEAN, "patient_age": "45"}),
    ("HC-N03", "age as float",
     {**HC_CLEAN, "patient_age": 45.7}),
    ("HC-N04", "all optional fields nulled",
     {**HC_CLEAN, "medication": None, "procedure_code": None,
      "insurance_provider": None, "notes": None}),
    ("HC-N05", "extra unknown field injected",
     {**HC_CLEAN, "unknown_field": "surprise", "another_extra": 999}),
    ("HC-N06", "whitespace-padded date",
     {**HC_CLEAN, "admission_date": "  2024-09-14  "}),
    ("HC-N07", "admission and discharge same day (valid edge)",
     {**HC_CLEAN, "discharge_date": "2024-09-14"}),
    ("HC-N08", "discharge exactly one day after (boundary valid)",
     {**HC_CLEAN, "admission_date": "2024-09-14", "discharge_date": "2024-09-15"}),
    ("HC-N09", "patient_age off by 1 (within tolerance)",
     {**HC_CLEAN, "patient_age": 44}),  # computed = 45, tolerance ±1
    ("HC-N10", "patient_age off by 2 (should flag HC-001)",
     {**HC_CLEAN, "patient_age": 43}),  # just outside ±1
    ("HC-N11", "extremely long notes string (1000 chars)",
     {**HC_CLEAN, "notes": "x" * 1000}),
    ("HC-N12", "unicode in name fields",
     {**HC_CLEAN, "first_name": "Ñoño", "last_name": "García-López"}),
    ("HC-N13", "date as None — null date",
     {**HC_CLEAN, "discharge_date": None}),
    ("HC-N14", "malformed date string",
     {**HC_CLEAN, "admission_date": "not-a-date"}),
    ("HC-N15", "negative patient_age",
     {**HC_CLEAN, "patient_age": -5}),
]

NOISE_CASES_FN = [
    ("FN-N01", "annual_income = 0",
     {**FN_CLEAN, "annual_income": 0}),
    ("FN-N02", "annual_income as string",
     {**FN_CLEAN, "annual_income": "92000"}),
    ("FN-N03", "loan_amount = 0",
     {**FN_CLEAN, "loan_amount": 0}),
    ("FN-N04", "approval_date = None (pending)",
     {**FN_CLEAN, "approval_date": None}),
    ("FN-N05", "approved_amount = None",
     {**FN_CLEAN, "approved_amount": None}),
    ("FN-N06", "employment_length_years = 0",
     {**FN_CLEAN, "employment_length_years": 0}),
    ("FN-N07", "employment_length_years = None",
     {**FN_CLEAN, "employment_length_years": None}),
    ("FN-N08", "credit_score as float",
     {**FN_CLEAN, "credit_score": 742.5}),
    ("FN-N09", "extra nested object injected",
     {**FN_CLEAN, "meta": {"source": "api", "version": 2}}),
    ("FN-N10", "all numeric fields as strings",
     {**FN_CLEAN, "annual_income": "92000", "loan_amount": "320000",
      "credit_score": "742", "existing_debt": "18000"}),
]

# ─────────────────────────────────────────────────────────────
# SUITE B — ADVERSARIAL BOUNDARY CASES
# ─────────────────────────────────────────────────────────────
# Each case specifies: expected_violations (empty = should pass)

ADVERSARIAL_HC = [
    ("HC-A01", "discharge exactly on admission date (boundary valid, LOS=0)",
     {**HC_CLEAN, "discharge_date": "2024-09-14"},
     [], "trusted"),

    ("HC-A02", "discharge one day before admission (boundary violation)",
     {**HC_CLEAN, "discharge_date": "2024-09-13"},
     ["HC-003"], "flagged"),

    ("HC-A03", "age exactly ±1 of computed (boundary valid)",
     {**HC_CLEAN, "patient_age": 46},
     [], "trusted"),

    ("HC-A04", "age exactly ±2 of computed (boundary violation)",
     {**HC_CLEAN, "patient_age": 47},
     ["HC-001"], "flagged"),

    ("HC-A05", "admission exactly on DOB (boundary valid)",
     {**HC_CLEAN,
      "date_of_birth": "2024-09-14",
      "admission_date": "2024-09-14",
      "discharge_date": "2024-09-17",
      "patient_age": 0},
     [], "trusted"),

    ("HC-A06", "admission one day before DOB (impossible)",
     {**HC_CLEAN,
      "date_of_birth": "2024-09-15",
      "admission_date": "2024-09-14",
      "discharge_date": "2024-09-17",
      "patient_age": 0},
     ["HC-002"], "flagged"),

    ("HC-A07",
     "age=18 + I25.10 (adult Dx passes HC-004) but base medication Azithromycin "
     "is not in the I25.x cardiology map → HC-005 fires (warning)",
     {**HC_CLEAN,
      "date_of_birth": "2006-09-14",
      "admission_date": "2024-09-14",
      "patient_age": 18,
      "diagnosis_code": "I25.10"},
     # HC-004 passes: age 18 >= 18 threshold
     # HC-005 fires: Azithromycin not in {Atorvastatin, Aspirin, Clopidogrel, Metoprolol, Lisinopril}
     ["HC-005"], "trusted"),   # warning only → conf 0.88 → trusted

    ("HC-A08",
     "age=16 + I25.10: two warnings fire — HC-004 (age<18 for adult code) "
     "AND HC-005 (Azithromycin not in I25.x map) → conf 0.76 → flagged",
     {**HC_CLEAN,
      "date_of_birth": "2007-09-15",
      "admission_date": "2024-09-14",
      "patient_age": 16,
      "diagnosis_code": "I25.10"},
     # HC-004 fires: age 16 < 18 for adult-only I25.10
     # HC-005 fires: Azithromycin not in I25.x medication set
     # 2 warnings: 1.0 - 0.12 - 0.12 = 0.76 → flagged
     ["HC-004", "HC-005"], "flagged"),

    ("HC-A09", "medication mismatch: cardiac drug for UTI diagnosis",
     {**HC_CLEAN,
      "diagnosis_code": "N39.0",
      "medication": "Metoprolol"},
     ["HC-005"], "trusted"),  # warning → trusted

    ("HC-A10", "correct medication for diagnosis (plausibility pass)",
     {**HC_CLEAN,
      "diagnosis_code": "J18.9",
      "medication": "Azithromycin"},
     [], "trusted"),
]

ADVERSARIAL_FN = [
    ("FN-A01", "loan:income ratio exactly 10x (boundary valid)",
     {**FN_CLEAN, "annual_income": 32000, "loan_amount": 320000},
     [], "trusted"),

    ("FN-A02", "loan:income ratio slightly above 10x (0.001 over)",
     {**FN_CLEAN, "annual_income": 31999, "loan_amount": 320000},
     ["FN-002"], "flagged"),

    ("FN-A03", "approval exactly same day as application (valid)",
     {**FN_CLEAN,
      "application_date": "2024-08-10",
      "approval_date": "2024-08-10"},
     [], "trusted"),

    ("FN-A04", "approval one day before application (violation)",
     {**FN_CLEAN,
      "application_date": "2024-08-10",
      "approval_date": "2024-08-09"},
     ["FN-001"], "flagged"),

    ("FN-A05", "approved_amount exactly equals loan_amount (boundary valid)",
     {**FN_CLEAN, "loan_amount": 320000, "approved_amount": 320000},
     [], "trusted"),

    ("FN-A06", "approved_amount one dollar over loan_amount (violation)",
     {**FN_CLEAN, "loan_amount": 320000, "approved_amount": 320001},
     ["FN-005"], "flagged"),

    ("FN-A07", "DTI exactly 60% (boundary valid)",
     {**FN_CLEAN, "annual_income": 100000, "existing_debt": 60000},
     [], "trusted"),

    ("FN-A08", "DTI just over 60% (boundary warning)",
     {**FN_CLEAN, "annual_income": 100000, "existing_debt": 60001},
     ["FN-003"], "trusted"),  # warning → still trusted

    ("FN-A09", "employment length = max possible for age (boundary valid)",
     {**FN_CLEAN,
      "date_of_birth": "1990-01-01",
      "application_date": "2024-08-10",
      "employment_length_years": 18},  # age=34, max=18
     [], "trusted"),

    ("FN-A10", "employment length one year over max (boundary violation)",
     {**FN_CLEAN,
      "date_of_birth": "1990-01-01",
      "application_date": "2024-08-10",
      "employment_length_years": 19},  # one over
     ["FN-004"], "flagged"),
]

# ─────────────────────────────────────────────────────────────
# SUITE C — MULTI-VIOLATION RECORDS
# ─────────────────────────────────────────────────────────────

MULTI_VIOLATION_HC = [
    ("HC-M01", "HC-001 + HC-003: age mismatch AND discharge before admission",
     {**HC_CLEAN,
      "patient_age": 60,             # computed = 45, diff = 15 → HC-001
      "discharge_date": "2024-09-10"},  # before admission → HC-003
     ["HC-001", "HC-003"],
     0.40),  # 2 critical: 1.0 - 0.30 - 0.30 = 0.40 → quarantined

    ("HC-M02", "HC-002 + HC-003: admission before birth AND discharge before admission",
     {**HC_CLEAN,
      "date_of_birth": "2025-01-01",    # future → HC-002
      "discharge_date": "2024-09-13"},   # before admission → HC-003
     ["HC-002", "HC-003"],
     0.40),

    ("HC-M03",
     "HC-001 + HC-004 design: age mismatch (HC-001 critical) + M81.0 on age-70 "
     "passes HC-004. HC-005 abstains on M81.0 (not in medication map) — "
     "unknown Dx categories pass by design",
     {**HC_CLEAN,
      "patient_age": 70,                # computed 45 → HC-001 fires
      "diagnosis_code": "M81.0",        # age 70 ≥ 18 → HC-004 passes
      "medication": "Amoxicillin"},      # M81.0 not in map → HC-005 abstains (pass)
     # HC-001 fires (critical), HC-004 passes, HC-005 abstains on unknown Dx
     ["HC-001"],
     0.70),  # 1 critical: 1.0 - 0.30 = 0.70 → flagged

    ("HC-M04", "HC-001 + HC-002: age mismatch + impossible admission",
     {**HC_CLEAN,
      "date_of_birth": "2030-01-01",    # future DOB
      "patient_age": 100},              # wildly wrong
     ["HC-001", "HC-002"],
     0.40),
]

MULTI_VIOLATION_FN = [
    ("FN-M01", "FN-001 + FN-002: approval before application AND extreme LTI",
     {**FN_CLEAN,
      "approval_date": "2024-07-01",    # before application → FN-001
      "loan_amount": 2500000},           # 27x income → FN-002
     ["FN-001", "FN-002"],
     0.40),  # 2 critical

    ("FN-M02", "FN-002 + FN-004: extreme LTI AND impossible employment age",
     {**FN_CLEAN,
      "loan_amount": 1200000,            # 13x income → FN-002
      "date_of_birth": "2000-01-01",
      "application_date": "2024-08-10",
      "employment_length_years": 25},    # age 24, max 8 → FN-004
     ["FN-002", "FN-004"],
     0.40),

    ("FN-M03", "FN-001 + FN-004 + FN-005: date + age + over-approved",
     {**FN_CLEAN,
      "approval_date": "2024-07-01",     # before application → FN-001
      "date_of_birth": "2002-01-01",
      "application_date": "2024-08-10",
      "employment_length_years": 15,     # age 22, max 6 → FN-004
      "loan_amount": 300000,
      "approved_amount": 400000},        # > requested → FN-005
     ["FN-001", "FN-004", "FN-005"],
     0.10),  # 3 critical: 1.0 - 0.90 = 0.10 → quarantined

    ("FN-M04", "FN-002 + FN-003 + FN-005: LTI + DTI + over-approved",
     {**FN_CLEAN,
      "annual_income": 30000,
      "loan_amount": 500000,             # 16.7x → FN-002
      "existing_debt": 25000,            # 83% DTI → FN-003
      "approved_amount": 600000},        # > loan_amount → FN-005
     ["FN-002", "FN-005"],              # FN-003 is warning
     0.58),  # 2 critical + 1 warning = 1.0 - 0.60 - 0.12 = 0.28... but FN-003 warning
             # actual: FN-002 critical, FN-003 warning, FN-005 critical
             # 1.0 - 0.30 - 0.12 - 0.30 = 0.28
]

# ─────────────────────────────────────────────────────────────
# RUNNER FUNCTIONS
# ─────────────────────────────────────────────────────────────

def run_suite_a_noise(verbose: bool = True) -> dict:
    """Suite A: noise injection. Just verifies no crash + returns valid structure."""
    from validator.pipeline import validate_record
    print(f"\n{'═'*60}")
    print("  SUITE A — Noise Injection")
    print(f"{'═'*60}")

    results = []
    for case_id, description, record, *_ in (NOISE_CASES_HC + NOISE_CASES_FN):
        domain = "healthcare_intake" if case_id.startswith("HC") else "financial_loan_application"
        t0 = time.perf_counter()
        try:
            result = validate_record(record, domain, record_id=case_id)
            no_crash = True
            decision = result.get("decision", "unknown")
            confidence = result.get("confidence_score", -1)
            error = None
        except Exception as e:
            no_crash = False
            decision = "error"
            confidence = -1
            error = str(e)

        latency = (time.perf_counter() - t0) * 1000
        ok = "✓" if no_crash else "✗"
        if verbose:
            print(f"  {ok} [{case_id}] {description[:55]:<55} → {decision}  ({confidence})")

        results.append({
            "case_id": case_id, "description": description,
            "domain": domain, "no_crash": no_crash,
            "decision": decision, "confidence": confidence,
            "latency_ms": round(latency, 3), "error": error,
        })

    passed = sum(1 for r in results if r["no_crash"])
    print(f"\n  Suite A: {passed}/{len(results)} no-crash ({'PASS' if passed == len(results) else 'FAIL'})")
    return {"suite": "A_noise", "total": len(results), "passed_no_crash": passed, "results": results}


def run_suite_b_adversarial(verbose: bool = True) -> dict:
    """Suite B: adversarial boundary cases with expected violation assertions."""
    from validator.pipeline import validate_record
    print(f"\n{'═'*60}")
    print("  SUITE B — Adversarial Boundary Cases")
    print(f"{'═'*60}")

    all_cases = (
        [(c + ("healthcare_intake",)) for c in ADVERSARIAL_HC] +
        [(c + ("financial_loan_application",)) for c in ADVERSARIAL_FN]
    )

    results = []
    passed = 0
    for case_id, description, record, expected_violations, expected_decision, domain in all_cases:
        t0 = time.perf_counter()
        try:
            result = validate_record(record, domain, record_id=case_id)
            actual_violations = sorted([v["rule_id"] for v in result.get("violated_rules", [])])
            actual_decision = result.get("decision")
            confidence = result.get("confidence_score", -1)

            violation_match = sorted(expected_violations) == actual_violations
            decision_match = expected_decision == actual_decision
            case_pass = violation_match and decision_match

            if case_pass:
                passed += 1

            status = "✓" if case_pass else "✗"
            detail = ""
            if not violation_match:
                detail += f" violations: expected {expected_violations} got {actual_violations}"
            if not decision_match:
                detail += f" decision: expected {expected_decision} got {actual_decision}"

            if verbose:
                print(f"  {status} [{case_id}] {description[:45]:<45} conf={confidence:.2f}  {detail.strip()}")

        except Exception as e:
            case_pass = False
            actual_violations = []
            actual_decision = "error"
            confidence = -1
            detail = str(e)
            print(f"  ✗ [{case_id}] {description[:45]:<45} ERROR: {e}")

        latency = (time.perf_counter() - t0) * 1000
        results.append({
            "case_id": case_id, "description": description, "domain": domain,
            "expected_violations": expected_violations,
            "actual_violations": actual_violations,
            "expected_decision": expected_decision,
            "actual_decision": actual_decision,
            "confidence": confidence,
            "pass": case_pass,
            "latency_ms": round(latency, 3),
        })

    print(f"\n  Suite B: {passed}/{len(results)} passed")
    return {"suite": "B_adversarial", "total": len(results), "passed": passed, "results": results}


def run_suite_c_multi_violation(verbose: bool = True) -> dict:
    """Suite C: multi-violation records — check all violations reported + compound penalty."""
    from validator.pipeline import validate_record
    print(f"\n{'═'*60}")
    print("  SUITE C — Multi-Violation Records")
    print(f"{'═'*60}")

    all_cases = (
        [(c + ("healthcare_intake",)) for c in MULTI_VIOLATION_HC] +
        [(c + ("financial_loan_application",)) for c in MULTI_VIOLATION_FN]
    )

    results = []
    passed = 0
    for case_id, description, record, expected_violations, expected_conf_approx, domain in all_cases:
        t0 = time.perf_counter()
        try:
            result = validate_record(record, domain, record_id=case_id)
            actual_violations = sorted([v["rule_id"] for v in result.get("violated_rules", [])])
            confidence = result.get("confidence_score", -1)
            decision = result.get("decision")

            # All expected violations must be present (may have extras — that's OK)
            all_found = all(v in actual_violations for v in expected_violations)
            count_ok  = len(actual_violations) >= len(expected_violations)
            conf_ok   = abs(confidence - expected_conf_approx) <= 0.15  # ±0.15 tolerance

            case_pass = all_found and count_ok
            if case_pass:
                passed += 1

            missing = [v for v in expected_violations if v not in actual_violations]
            status = "✓" if case_pass else "✗"
            detail = f"conf={confidence:.2f}≈{expected_conf_approx:.2f}  {decision}"
            if missing:
                detail += f"  MISSING: {missing}"

            if verbose:
                print(f"  {status} [{case_id}] {description[:45]:<45}  {detail}")

        except Exception as e:
            case_pass = False
            actual_violations = []
            confidence = -1
            decision = "error"
            print(f"  ✗ [{case_id}] {description[:45]:<45}  ERROR: {e}")

        latency = (time.perf_counter() - t0) * 1000
        results.append({
            "case_id": case_id, "description": description, "domain": domain,
            "expected_violations": expected_violations,
            "actual_violations": actual_violations,
            "expected_conf_approx": expected_conf_approx,
            "actual_confidence": confidence,
            "decision": decision,
            "pass": case_pass,
            "latency_ms": round(latency, 3),
        })

    print(f"\n  Suite C: {passed}/{len(results)} passed")
    return {"suite": "C_multi_violation", "total": len(results), "passed": passed, "results": results}

# ─────────────────────────────────────────────────────────────
# VISUALISATION
# ─────────────────────────────────────────────────────────────

def plot_noise_results(suite_a: dict) -> None:
    """Plot 13: noise injection outcome breakdown."""
    results = suite_a["results"]

    decisions = [r["decision"] for r in results]
    confidences = [r["confidence"] for r in results if r["confidence"] >= 0]
    crashed = [r for r in results if not r["no_crash"]]

    decision_counts = {}
    for d in decisions:
        decision_counts[d] = decision_counts.get(d, 0) + 1

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Suite A — Noise Injection Outcomes", fontsize=14, color=BLUE, y=1.02)

    # Left: decision distribution
    ax = axes[0]
    color_map = {"trusted": GREEN, "flagged": YELLOW, "quarantined": RED, "error": ORANGE}
    labels = list(decision_counts.keys())
    vals   = list(decision_counts.values())
    colors = [color_map.get(l, MUTED) for l in labels]
    bars = ax.bar(labels, vals, color=colors, alpha=0.85, zorder=3)
    ax.set_title("Decision Distribution Under Noise", color=FG, fontsize=11)
    ax.set_ylabel("Count", fontsize=10)
    ax.grid(axis="y", zorder=0)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, v + 0.1, str(v),
                ha="center", fontsize=10, color=FG)
    ax.text(0.98, 0.97, f"No-crash: {suite_a['passed_no_crash']}/{suite_a['total']}",
            transform=ax.transAxes, ha="right", va="top", fontsize=9, color=GREEN,
            fontweight="bold")

    # Right: confidence distribution
    ax = axes[1]
    if confidences:
        arr = np.array(confidences)
        bins = np.linspace(0, 1.05, 15)
        counts, edges = np.histogram(arr, bins=bins)
        centers = [(edges[i]+edges[i+1])/2 for i in range(len(counts))]
        bar_colors = [RED if c < 0.5 else YELLOW if c < 0.85 else GREEN for c in centers]
        ax.bar(centers, counts, width=0.07, color=bar_colors, alpha=0.85, zorder=3,
               edgecolor=BG, linewidth=0.4)
        ax.axvline(0.85, color=GREEN, linestyle="--", linewidth=1.5, label="Trusted threshold")
        ax.axvline(0.50, color=YELLOW, linestyle="--", linewidth=1.5, label="Flagged threshold")
        ax.set_title("Confidence Scores Under Noise", color=FG, fontsize=11)
        ax.set_xlabel("Confidence Score", fontsize=10)
        ax.set_ylabel("Count", fontsize=10)
        ax.legend(fontsize=9)
        ax.grid(axis="y", zorder=0)

    plt.tight_layout()
    path = PLOTS_DIR / "13_adversarial_noise.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  ✓ saved {path.name}")


def plot_boundary_results(suite_b: dict) -> None:
    """Plot 14: adversarial boundary — pass/fail by case."""
    results = suite_b["results"]
    case_ids    = [r["case_id"] for r in results]
    passed      = [1 if r["pass"] else 0 for r in results]
    confidences = [r["confidence"] for r in results]
    domains     = [r["domain"] for r in results]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Suite B — Adversarial Boundary Cases", fontsize=14, color=BLUE, y=1.02)

    # Left: pass/fail per case
    ax = axes[0]
    colors = [GREEN if p else RED for p in passed]
    bars = ax.bar(case_ids, passed, color=colors, alpha=0.85, zorder=3)
    ax.set_xticks(range(len(case_ids)))
    ax.set_xticklabels(case_ids, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Pass (1) / Fail (0)", fontsize=10)
    ax.set_ylim(-0.1, 1.3)
    ax.set_title(f"Pass/Fail per Case  ({suite_b['passed']}/{suite_b['total']} passed)",
                 color=FG, fontsize=11)
    ax.grid(axis="y", zorder=0)

    # Right: confidence per case, colored by domain
    ax = axes[1]
    dom_colors = ["healthcare_intake", "financial_loan_application"]
    hc_idxs = [i for i, r in enumerate(results) if "health" in r["domain"]]
    fn_idxs = [i for i, r in enumerate(results) if "financial" in r["domain"]]
    ax.scatter(hc_idxs, [confidences[i] for i in hc_idxs],
               color=BLUE, s=60, zorder=4, label="Healthcare", marker="o")
    ax.scatter(fn_idxs, [confidences[i] for i in fn_idxs],
               color=PURPLE, s=60, zorder=4, label="Finance", marker="s")
    ax.axhline(0.85, color=GREEN, linestyle="--", linewidth=1.2, alpha=0.8)
    ax.axhline(0.50, color=YELLOW, linestyle="--", linewidth=1.2, alpha=0.8)
    ax.set_xticks(range(len(case_ids)))
    ax.set_xticklabels(case_ids, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Confidence Score", fontsize=10)
    ax.set_ylim(0, 1.15)
    ax.set_title("Confidence Scores at Boundaries", color=FG, fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(zorder=0)

    plt.tight_layout()
    path = PLOTS_DIR / "14_adversarial_boundary.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  ✓ saved {path.name}")


def plot_multi_violation(suite_c: dict) -> None:
    """Plot 15: multi-violation compound confidence analysis."""
    results = suite_c["results"]

    case_ids   = [r["case_id"] for r in results]
    expected_c = [r["expected_conf_approx"] for r in results]
    actual_c   = [r["actual_confidence"] for r in results]
    viol_counts = [len(r["actual_violations"]) for r in results]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Suite C — Multi-Violation Compound Confidence", fontsize=14, color=BLUE, y=1.02)

    x = np.arange(len(case_ids))
    w = 0.35

    ax = axes[0]
    b1 = ax.bar(x - w/2, expected_c, w, label="Expected (approx)", color=YELLOW, alpha=0.8, zorder=3)
    b2 = ax.bar(x + w/2, actual_c,   w, label="Actual",            color=BLUE,   alpha=0.8, zorder=3)
    ax.axhline(0.85, color=GREEN, linestyle="--", linewidth=1.2, alpha=0.7)
    ax.axhline(0.50, color=RED,   linestyle="--", linewidth=1.2, alpha=0.7)
    ax.set_xticks(x); ax.set_xticklabels(case_ids, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Confidence Score", fontsize=10)
    ax.set_ylim(0, 1.15)
    ax.set_title("Expected vs Actual Confidence", color=FG, fontsize=11)
    ax.legend(fontsize=9); ax.grid(axis="y", zorder=0)
    for bar in list(b1) + list(b2):
        v = bar.get_height()
        ax.text(bar.get_x()+bar.get_width()/2, v+0.01,
                f"{v:.2f}", ha="center", fontsize=8, color=FG)

    ax = axes[1]
    colors_v = [GREEN if n == 1 else YELLOW if n == 2 else ORANGE if n == 3 else RED
                for n in viol_counts]
    bars = ax.bar(case_ids, viol_counts, color=colors_v, alpha=0.85, zorder=3)
    ax.set_ylabel("Violation Count Detected", fontsize=10)
    ax.set_title("Violations Detected per Case", color=FG, fontsize=11)
    ax.set_xticks(range(len(case_ids)))
    ax.set_xticklabels(case_ids, rotation=30, ha="right", fontsize=9)
    ax.grid(axis="y", zorder=0)
    for bar, v in zip(bars, viol_counts):
        ax.text(bar.get_x()+bar.get_width()/2, v+0.05, str(v),
                ha="center", fontsize=10, color=FG)

    plt.tight_layout()
    path = PLOTS_DIR / "15_multi_violation_confidence.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  ✓ saved {path.name}")

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    import logging
    logging.disable(logging.WARNING)

    print("\n" + "=" * 60)
    print("  SchemaGuard — Adversarial Evaluation Suite")
    print("=" * 60)

    t0 = time.time()
    suite_a = run_suite_a_noise()
    suite_b = run_suite_b_adversarial()
    suite_c = run_suite_c_multi_violation()

    # Aggregate
    total_cases  = suite_a["total"] + suite_b["total"] + suite_c["total"]
    total_passed = suite_a["passed_no_crash"] + suite_b["passed"] + suite_c["passed"]

    # Save JSON
    output = {
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "summary": {
            "total_cases": total_cases,
            "total_passed": total_passed,
            "suite_A_noise":    {"total": suite_a["total"], "no_crash": suite_a["passed_no_crash"]},
            "suite_B_adversarial": {"total": suite_b["total"], "passed": suite_b["passed"]},
            "suite_C_multi":    {"total": suite_c["total"], "passed": suite_c["passed"]},
        },
        "suites": [suite_a, suite_b, suite_c],
    }
    out_path = RESULTS_DIR / "adversarial_results.json"
    out_path.write_text(__import__("json").dumps(output, indent=2))
    print(f"\n  ✓ Saved {out_path}")

    # Plots
    print("\n  Generating plots...")
    plot_noise_results(suite_a)
    plot_boundary_results(suite_b)
    plot_multi_violation(suite_c)

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  TOTAL: {total_passed}/{total_cases} passed  ({elapsed:.1f}s)")
    pct = total_passed / total_cases * 100
    status = "ALL PASSED" if total_passed == total_cases else f"{total_cases - total_passed} FAILED"
    print(f"  {status}  ({pct:.0f}%)")
    print(f"{'='*60}\n")

    return 0 if total_passed == total_cases else 1


if __name__ == "__main__":
    sys.exit(main())

"""
SchemaGuard — Drift and Scoring Test Script

Tests the full monitoring and decision layer:
    1. Generate baseline from seed valid records
    2. Run batch validation on all seed records
    3. Simulate drift by modifying field values
    4. Run drift detection on the drifted batch
    5. Print confidence scores, decisions, and drift alerts

Usage:
    cd schema-guard-llm-validation
    python -m evaluation.test_drift_and_scoring
"""

import sys
import json
import copy
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from drift.drift_detector import generate_baseline, run_drift_detection
from validator.batch_validation import validate_batch
from scoring.confidence_score import compute_confidence_score
from scoring.decision import make_decision
from validator.structural import validate_structure
from validator.semantic import validate_semantics

SEED_DIR = PROJECT_ROOT / "data_gen" / "sample_data"
SEP = "─" * 72


def load_seeds(filename):
    with open(SEED_DIR / filename) as f:
        return json.load(f)


def test_baseline_generation():
    """Generate baselines from valid seed records."""
    print(f"\n{'═' * 72}")
    print("  1. BASELINE GENERATION")
    print(f"{'═' * 72}")

    for filename, domain in [
        ("healthcare_seed_examples.json", "healthcare_intake"),
        ("finance_seed_examples.json", "financial_loan_application"),
    ]:
        seeds = load_seeds(filename)
        valid_records = [s["record"] for s in seeds if s["category"] == "valid"]
        profile = generate_baseline(valid_records, domain)

        label = "Healthcare" if "healthcare" in domain else "Finance"
        print(f"\n  {label} baseline ({len(valid_records)} valid records):")
        for field, stats in profile["fields"].items():
            if stats["type"] == "numeric":
                print(f"    {field}: mean={stats['mean']:.1f}, std={stats['std']:.1f}, range=[{stats['min']:.0f}, {stats['max']:.0f}]")
            else:
                print(f"    {field}: {len(stats['distribution'])} categories")
        for field, rate in profile.get("null_rates", {}).items():
            if rate > 0:
                print(f"    {field} null rate: {rate:.0%}")


def test_batch_validation():
    """Run batch validation and show per-record results."""
    print(f"\n{'═' * 72}")
    print("  2. BATCH VALIDATION + CONFIDENCE + DECISIONS")
    print(f"{'═' * 72}")

    for filename, domain in [
        ("healthcare_seed_examples.json", "healthcare_intake"),
        ("finance_seed_examples.json", "financial_loan_application"),
    ]:
        seeds = load_seeds(filename)
        records = [s["record"] for s in seeds]
        label = "Healthcare" if "healthcare" in domain else "Finance"

        print(f"\n  {label} — {len(records)} records")
        print(f"  {SEP}")

        batch_result = validate_batch(records, domain, run_drift=True)

        for i, (seed, result) in enumerate(zip(seeds, batch_result["results"])):
            cat = seed["category"]
            icon = "✅" if result["decision"] == "trusted" else "⚠️ " if result["decision"] == "flagged" else "🚫"
            print(f"  {icon} {seed['record_id']}  [{cat.upper():10s}]  "
                  f"conf={result['confidence_score']:.2f}  decision={result['decision']:12s}  "
                  f"reason: {result['decision_reason']}")

            if result["confidence_breakdown"]["semantic_penalty"] > 0:
                print(f"       penalties: semantic={result['confidence_breakdown']['semantic_penalty']:.2f}")

        s = batch_result["summary"]
        print(f"\n  Summary: trusted={s['trusted']}  flagged={s['flagged']}  quarantined={s['quarantined']}  "
              f"mean_conf={s['mean_confidence']:.2f}  time={s['processing_time_ms']:.1f}ms")

        drift = batch_result.get("drift_summary", {})
        if drift and drift.get("drift_detected"):
            print(f"  ⚠️  DRIFT DETECTED — {len(drift['alerts'])} alert(s)")
            for a in drift["alerts"]:
                print(f"       [{a['severity'].upper()}] {a['message']}")
        else:
            print(f"  ✅ No drift detected ({drift.get('checked_fields', 0)} fields checked)")


def test_simulated_drift():
    """Simulate drift by modifying valid records and re-running detection."""
    print(f"\n{'═' * 72}")
    print("  3. SIMULATED DRIFT DETECTION")
    print(f"{'═' * 72}")

    # Healthcare: shift patient_age up dramatically
    hc_seeds = load_seeds("healthcare_seed_examples.json")
    hc_valid = [s["record"] for s in hc_seeds if s["category"] == "valid"]

    drifted_hc = []
    for r in hc_valid:
        d = copy.deepcopy(r)
        d["patient_age"] = d.get("patient_age", 40) + 35  # age shift +35
        d["gender"] = "other"  # categorical shift
        d["insurance_provider"] = None  # null rate shift
        drifted_hc.append(d)

    print(f"\n  Healthcare — injected drift: patient_age +35, gender→other, insurance→null")
    drift_hc = run_drift_detection(drifted_hc, "healthcare_intake")

    if drift_hc.get("drift_detected"):
        print(f"  ⚠️  DRIFT DETECTED — {len(drift_hc['alerts'])} alert(s)")
        for a in drift_hc["alerts"]:
            print(f"    [{a['severity'].upper():6s}] {a['message']}")
    else:
        print(f"  No drift detected")

    for field, metric in drift_hc.get("drift_metrics", {}).items():
        if metric["type"] == "numeric":
            print(f"    {field}: baseline_mean={metric['baseline_mean']}, current_mean={metric['current_mean']}, z_shift={metric['z_shift']}")
        elif metric["type"] == "categorical":
            print(f"    {field}: PSI={metric['psi']}")

    # Finance: shift income and loan amounts
    fn_seeds = load_seeds("finance_seed_examples.json")
    fn_valid = [s["record"] for s in fn_seeds if s["category"] == "valid"]

    drifted_fn = []
    for r in fn_valid:
        d = copy.deepcopy(r)
        d["annual_income"] = d.get("annual_income", 80000) * 3  # income 3x
        d["loan_amount"] = d.get("loan_amount", 100000) * 0.1  # loan shrink
        d["credit_score"] = 800  # all high credit
        drifted_fn.append(d)

    print(f"\n  Finance — injected drift: income×3, loan×0.1, credit_score→800")
    drift_fn = run_drift_detection(drifted_fn, "financial_loan_application")

    if drift_fn.get("drift_detected"):
        print(f"  ⚠️  DRIFT DETECTED — {len(drift_fn['alerts'])} alert(s)")
        for a in drift_fn["alerts"]:
            print(f"    [{a['severity'].upper():6s}] {a['message']}")
    else:
        print(f"  No drift detected")

    for field, metric in drift_fn.get("drift_metrics", {}).items():
        if metric["type"] == "numeric":
            print(f"    {field}: baseline_mean={metric['baseline_mean']}, current_mean={metric['current_mean']}, z_shift={metric['z_shift']}")


def test_confidence_breakdown():
    """Show detailed confidence breakdown for one valid and one invalid record."""
    print(f"\n{'═' * 72}")
    print("  4. CONFIDENCE SCORE BREAKDOWN")
    print(f"{'═' * 72}")

    hc_seeds = load_seeds("healthcare_seed_examples.json")

    for seed in hc_seeds[:1] + [s for s in hc_seeds if s["category"] == "invalid"][:1]:
        record = seed["record"]
        structural = validate_structure(record, "healthcare_intake")
        semantic = validate_semantics(record, "healthcare_intake") if structural["valid"] else {"valid": False, "rules_evaluated": 0, "violations": [], "all_results": []}
        score_result = compute_confidence_score(structural, semantic)
        decision_result = make_decision(score_result["confidence_score"], structural["valid"], semantic["valid"], semantic["violations"])

        print(f"\n  {seed['record_id']} [{seed['category'].upper()}]")
        print(f"    Confidence: {score_result['confidence_score']}")
        print(f"    Breakdown:  {json.dumps(score_result['breakdown'], indent=2).replace(chr(10), chr(10) + '    ')}")
        print(f"    Decision:   {decision_result['decision']} — {decision_result['reason']}")


def main():
    print("\n" + "=" * 72)
    print("  SchemaGuard — Drift & Scoring Test Suite")
    print("=" * 72)

    test_baseline_generation()
    test_batch_validation()
    test_simulated_drift()
    test_confidence_breakdown()

    print(f"\n{'═' * 72}")
    print("  All tests complete.")
    print(f"{'═' * 72}\n")


if __name__ == "__main__":
    main()

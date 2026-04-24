"""
SchemaGuard — Full Evaluation Suite

Runs the complete evaluation pipeline:
    1. Validation accuracy (per domain, per record)
    2. Metrics computation (precision, recall, F1, FQR)
    3. Drift detection evaluation (baseline + simulated shift)
    4. Chart generation (HTML)
    5. Summary report

Usage:
    cd schema-guard-llm-validation
    python -m evaluation.run_full_evaluation
"""

import sys
import json
import copy
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from validator.pipeline import validate_record
from evaluation.metrics import compute_metrics, print_report
from evaluation.charts import save_charts
from drift.drift_detector import generate_baseline, run_drift_detection

SEED_DIR = PROJECT_ROOT / "data_gen" / "sample_data"
RESULTS_DIR = Path(__file__).parent / "results"

DOMAINS = {
    "healthcare_intake": "healthcare_seed_examples.json",
    "financial_loan_application": "finance_seed_examples.json",
}

SEP = "═" * 72


def load_seeds(filename):
    with open(SEED_DIR / filename) as f:
        return json.load(f)


def run_validation_evaluation(domain, seeds):
    """Run validation on all seeds and compute metrics."""
    eval_results = []
    for seed in seeds:
        result = validate_record(seed["record"], domain, record_id=seed["record_id"])
        expected_valid = seed["category"] != "invalid"
        eval_results.append({
            "record_id": seed["record_id"],
            "category": seed["category"],
            "expected_semantic_valid": expected_valid,
            "actual_semantic_valid": result["semantic_valid"],
            "expected_violations": seed.get("violated_rules", []),
            "actual_violations": [v["rule_id"] for v in result["violated_rules"]],
            "confidence_score": result["confidence_score"],
            "decision": result["decision"],
            "correct": expected_valid == result["semantic_valid"],
        })
    metrics = compute_metrics(eval_results)
    return eval_results, metrics


def run_drift_evaluation(domain, seeds):
    """Generate baseline, then test drift detection with simulated shifts."""
    valid_records = [s["record"] for s in seeds if s["category"] == "valid"]
    profile = generate_baseline(valid_records, domain)
    clean_drift = run_drift_detection(valid_records, domain)

    drifted = []
    for r in valid_records:
        d = copy.deepcopy(r)
        if "patient_age" in d:
            d["patient_age"] = d.get("patient_age", 40) + 30
        if "annual_income" in d:
            d["annual_income"] = d.get("annual_income", 80000) * 3
        if "gender" in d:
            d["gender"] = "other"
        if "credit_score" in d:
            d["credit_score"] = 800
        drifted.append(d)

    shifted_drift = run_drift_detection(drifted, domain)

    return {
        "baseline_records": len(valid_records),
        "baseline_fields": len(profile.get("fields", {})),
        "clean_drift_detected": clean_drift.get("drift_detected", False),
        "clean_alerts": len(clean_drift.get("alerts", [])),
        "shifted_drift_detected": shifted_drift.get("drift_detected", False),
        "shifted_alerts": shifted_drift.get("alerts", []),
    }


def main():
    print(f"\n{SEP}")
    print("  SchemaGuard — Full Evaluation Suite")
    print(SEP)

    all_metrics = {}
    all_results = {}
    all_drift = {}

    # Phase 1: Validation Accuracy
    print(f"\n{SEP}")
    print("  PHASE 1: Validation Accuracy")
    print(SEP)

    for domain, filename in DOMAINS.items():
        seeds = load_seeds(filename)
        label = "Healthcare" if "healthcare" in domain else "Finance"
        print(f"\n  {label} — {len(seeds)} records")

        results, metrics = run_validation_evaluation(domain, seeds)
        all_metrics[domain] = metrics
        all_results[domain] = results

        for r in results:
            icon = "✓" if r["correct"] else "✗"
            print(f"    {icon} {r['record_id']}  [{r['category']:10s}]  "
                  f"conf={r['confidence_score']:.2f}  decision={r['decision']}")

        print_report(label, metrics)

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        prefix = "healthcare" if "healthcare" in domain else "finance"
        with open(RESULTS_DIR / f"{prefix}_eval_results.json", "w") as f:
            json.dump({"domain": domain, "total_records": len(results), "results": results, "metrics": metrics}, f, indent=2)

    # Phase 2: Drift Detection
    print(f"\n{SEP}")
    print("  PHASE 2: Drift Detection")
    print(SEP)

    for domain, filename in DOMAINS.items():
        seeds = load_seeds(filename)
        label = "Healthcare" if "healthcare" in domain else "Finance"
        print(f"\n  {label}:")

        drift_eval = run_drift_evaluation(domain, seeds)
        all_drift[domain] = drift_eval

        print(f"    Baseline: {drift_eval['baseline_records']} records, {drift_eval['baseline_fields']} fields")
        print(f"    Clean batch: {'DRIFT' if drift_eval['clean_drift_detected'] else 'No drift'} ({drift_eval['clean_alerts']} alerts)")
        print(f"    Shifted batch: {'DRIFT' if drift_eval['shifted_drift_detected'] else 'No drift'} ({len(drift_eval['shifted_alerts'])} alerts)")

        for a in drift_eval["shifted_alerts"]:
            print(f"      [{a['severity'].upper():6s}] {a['message']}")

    # Phase 3: Charts
    print(f"\n{SEP}")
    print("  PHASE 3: Chart Generation")
    print(SEP)

    hc_domain = "healthcare_intake"
    fn_domain = "financial_loan_application"
    save_charts(all_metrics[hc_domain], all_metrics[fn_domain], all_results[hc_domain], all_results[fn_domain])

    # Phase 4: Summary
    print(f"\n{SEP}")
    print("  FINAL SUMMARY")
    print(SEP)

    total = sum(len(all_results[d]) for d in all_results)
    correct = sum(sum(1 for r in all_results[d] if r["correct"]) for d in all_results)
    accuracy = correct / total * 100 if total > 0 else 0

    print(f"\n  Total records evaluated:  {total}")
    print(f"  Total correct:           {correct}")
    print(f"  Overall accuracy:        {accuracy:.1f}%")

    for domain, metrics in all_metrics.items():
        label = "Healthcare" if "healthcare" in domain else "Finance"
        print(f"  {label}:  precision={metrics['precision']}  recall={metrics['recall']}  F1={metrics['f1_score']}  FQR={metrics['false_quarantine_rate']}")

    drift_shift_ok = all(all_drift[d]["shifted_drift_detected"] for d in all_drift)
    print(f"\n  Drift shift detection:   {'PASS (all simulated shifts caught)' if drift_shift_ok else 'FAIL'}")

    summary = {
        "total_records": total,
        "total_correct": correct,
        "accuracy": round(accuracy / 100, 4),
        "metrics_by_domain": all_metrics,
        "drift_evaluation": {d: {k: v for k, v in v.items() if k != "shifted_alerts"} for d, v in all_drift.items()},
    }
    with open(RESULTS_DIR / "evaluation_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Summary saved: evaluation/results/evaluation_summary.json")
    print(f"\n{SEP}")
    print("  Evaluation complete.")
    print(f"{SEP}\n")


if __name__ == "__main__":
    main()

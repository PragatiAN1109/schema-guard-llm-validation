"""
SchemaGuard — Evaluation Runner

Runs the full validation pipeline against labeled seed/generated datasets
and computes precision, recall, false-quarantine rate, and confidence separation.

Usage:
    cd schema-guard-llm-validation
    python -m evaluation.evaluate
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from validator.pipeline import validate_record
from evaluation.metrics import compute_metrics, print_report


SEED_DIR = Path(__file__).parent.parent / "data_gen" / "sample_data"
RESULTS_DIR = Path(__file__).parent / "results"

SEED_FILES = {
    "healthcare_intake": "healthcare_seed_examples.json",
    "financial_loan_application": "finance_seed_examples.json",
}


def load_seed_data(domain: str) -> list[dict]:
    """Load labeled seed records for a domain."""
    filename = SEED_FILES.get(domain)
    if not filename:
        raise ValueError(f"No seed data for domain: {domain}")
    path = SEED_DIR / filename
    with open(path) as f:
        return json.load(f)


def run_evaluation(domain: str) -> dict:
    """
    Run validation on all seed records for a domain and compare
    pipeline output against ground-truth labels.
    """
    seeds = load_seed_data(domain)
    eval_results = []

    for seed in seeds:
        record = seed["record"]
        record_id = seed["record_id"]
        expected_category = seed["category"]
        expected_valid = expected_category != "invalid"
        expected_violations = seed.get("violated_rules", [])

        # Run pipeline
        result = validate_record(record, domain, record_id=record_id)

        eval_results.append({
            "record_id": record_id,
            "category": expected_category,
            "expected_semantic_valid": expected_valid,
            "actual_semantic_valid": result["semantic_valid"],
            "expected_violations": expected_violations,
            "actual_violations": [v["rule_id"] for v in result["violated_rules"]],
            "confidence_score": result["confidence_score"],
            "decision": result["decision"],
            "correct": expected_valid == result["semantic_valid"],
        })

    return {
        "domain": domain,
        "total_records": len(eval_results),
        "results": eval_results,
    }


def save_results(eval_output: dict, domain: str) -> None:
    """Save evaluation results to JSON."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    prefix = "healthcare" if "healthcare" in domain else "finance"
    path = RESULTS_DIR / f"{prefix}_eval_results.json"
    with open(path, "w") as f:
        json.dump(eval_output, f, indent=2)
    print(f"Results saved to {path}")


def main():
    for domain in SEED_FILES:
        print(f"\n{'='*60}")
        print(f"Evaluating: {domain}")
        print(f"{'='*60}")

        eval_output = run_evaluation(domain)
        metrics = compute_metrics(eval_output["results"])
        print_report(domain, metrics)
        save_results({**eval_output, "metrics": metrics}, domain)


if __name__ == "__main__":
    main()

"""
SchemaGuard — Validation Test Script

Loads seed data from data_gen/sample_data/, runs the full validation
pipeline on every record, and prints structured results.

Usage:
    cd schema-guard-llm-validation
    python -m evaluation.test_validation
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from validator.pipeline import validate_record
from validator.schema_validator import validate_schema


SEED_DIR = PROJECT_ROOT / "data_gen" / "sample_data"

DOMAIN_MAP = {
    "healthcare_seed_examples.json": "healthcare_intake",
    "finance_seed_examples.json": "financial_loan_application",
}

SEPARATOR = "─" * 72


def load_seeds(filename: str) -> list[dict]:
    path = SEED_DIR / filename
    with open(path) as f:
        return json.load(f)


def print_result(seed: dict, result: dict):
    """Print a single validation result in readable format."""
    record_id = seed["record_id"]
    category = seed["category"]
    expected_valid = category != "invalid"
    actual_valid = result["semantic_valid"]
    match = "✓ CORRECT" if expected_valid == actual_valid else "✗ MISMATCH"

    print(f"\n  {record_id}  [{category.upper()}]  {match}")
    print(f"  Notes: {seed.get('notes', '—')}")
    print(f"  Structural:  {'PASS' if result['structural_valid'] else 'FAIL'}")
    print(f"  Semantic:    {'PASS' if result['semantic_valid'] else 'FAIL'}")
    print(f"  Confidence:  {result['confidence_score']}")
    print(f"  Decision:    {result['decision']}")

    if result["violated_rules"]:
        print(f"  Violations:")
        for v in result["violated_rules"]:
            print(f"    [{v['severity'].upper()}] {v['rule_id']} — {v['rule_name']}")
            print(f"      {v['message']}")

    print(f"  Explanation: {result['explanation'][:140]}...")


def run_domain_tests(filename: str, domain: str):
    """Run tests for one domain and print summary."""
    seeds = load_seeds(filename)
    domain_label = "Healthcare" if "healthcare" in domain else "Finance"

    print(f"\n{'═' * 72}")
    print(f"  {domain_label} Domain — {len(seeds)} seed records")
    print(f"{'═' * 72}")

    correct = 0
    total = 0

    for seed in seeds:
        record = seed["record"]
        result = validate_record(record, domain, record_id=seed["record_id"])

        expected_valid = seed["category"] != "invalid"
        actual_valid = result["semantic_valid"]
        if expected_valid == actual_valid:
            correct += 1
        total += 1

        print_result(seed, result)
        print(f"  {SEPARATOR}")

    # Schema validator interface tests
    print(f"\n  Schema Validator interface test:")
    schema_result = validate_schema(seeds[0]["record"], domain)
    print(f"    structural_valid: {schema_result['structural_valid']}, error_count: {schema_result['error_count']}")

    bad_json_result = validate_schema("{not valid json", domain)
    print(f"    bad JSON handled: structural_valid={bad_json_result['structural_valid']}")

    bad_type_result = validate_schema([1, 2, 3], domain)
    print(f"    bad type handled: structural_valid={bad_type_result['structural_valid']}")

    print(f"\n  Summary: {correct}/{total} records classified correctly")
    return correct, total


def main():
    print("\n" + "=" * 72)
    print("  SchemaGuard — Validation Test Suite")
    print("  Running against seed data")
    print("=" * 72)

    total_correct = 0
    total_records = 0

    for filename, domain in DOMAIN_MAP.items():
        c, t = run_domain_tests(filename, domain)
        total_correct += c
        total_records += t

    print(f"\n{'═' * 72}")
    print(f"  OVERALL: {total_correct}/{total_records} records classified correctly")
    accuracy = total_correct / total_records * 100 if total_records > 0 else 0
    print(f"  Accuracy: {accuracy:.1f}%")
    print(f"{'═' * 72}\n")


if __name__ == "__main__":
    main()

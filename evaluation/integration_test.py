"""
SchemaGuard — Integration Test

Tests the full system end-to-end:
    1. Single record validation (valid + invalid + edge case + bad input)
    2. Batch validation (normal + empty + mixed types)
    3. Drift detection (baseline + shift)
    4. Scoring + decision consistency

Usage:
    cd schema-guard-llm-validation
    python -m evaluation.integration_test
"""

import sys
import json
import copy
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from validator.pipeline import validate_record
from validator.batch_validation import validate_batch
from drift.drift_detector import generate_baseline, run_drift_detection

SEED_DIR = PROJECT_ROOT / "data_gen" / "sample_data"
PASS = "✓ PASS"
FAIL = "✗ FAIL"


def load_seeds(filename):
    with open(SEED_DIR / filename) as f:
        return json.load(f)


def check(label, condition):
    status = PASS if condition else FAIL
    print(f"    {status}  {label}")
    return condition


def test_single_validation():
    """Test single record validation with valid, invalid, and bad inputs."""
    print(f"\n  {'═' * 60}")
    print("  TEST 1: Single Record Validation")
    print(f"  {'═' * 60}")
    passed = total = 0

    hc = load_seeds("healthcare_seed_examples.json")
    fn = load_seeds("finance_seed_examples.json")

    # Valid healthcare
    r = validate_record(hc[0]["record"], "healthcare_intake")
    total += 3
    passed += check("Valid HC: structural=True", r["structural_valid"] is True)
    passed += check("Valid HC: semantic=True", r["semantic_valid"] is True)
    passed += check("Valid HC: decision=trusted", r["decision"] == "trusted")

    # Invalid healthcare (discharge before admission)
    r = validate_record(hc[3]["record"], "healthcare_intake")
    total += 3
    passed += check("Invalid HC: structural=True", r["structural_valid"] is True)
    passed += check("Invalid HC: semantic=False", r["semantic_valid"] is False)
    passed += check("Invalid HC: HC-003 caught", any(v["rule_id"] == "HC-003" for v in r["violated_rules"]))

    # Valid finance
    r = validate_record(fn[0]["record"], "financial_loan_application")
    total += 2
    passed += check("Valid FN: decision=trusted", r["decision"] == "trusted")
    passed += check("Valid FN: confidence=1.0", r["confidence_score"] == 1.0)

    # Edge case: None input
    r = validate_record(None, "healthcare_intake")
    total += 2
    passed += check("None input: no crash", r is not None)
    passed += check("None input: quarantined", r["decision"] == "quarantined")

    # Edge case: empty dict
    r = validate_record({}, "healthcare_intake")
    total += 1
    passed += check("Empty dict: quarantined", r["decision"] == "quarantined")

    # Edge case: non-dict inputs
    r = validate_record("not a dict", "healthcare_intake")
    total += 1
    passed += check("String input: quarantined", r["decision"] == "quarantined")

    r = validate_record([1, 2], "healthcare")
    total += 1
    passed += check("List input: quarantined", r["decision"] == "quarantined")

    r = validate_record(42, "healthcare")
    total += 1
    passed += check("Int input: quarantined", r["decision"] == "quarantined")

    # Edge case: bad domain
    r = validate_record(hc[0]["record"], "unknown_domain")
    total += 1
    passed += check("Bad domain: quarantined", r["decision"] == "quarantined")

    # Domain alias
    r = validate_record(hc[0]["record"], "healthcare")
    total += 1
    passed += check("Alias 'healthcare': resolves", r["structural_valid"] is True)

    print(f"\n    Single validation: {passed}/{total}")
    return passed, total


def test_batch_validation():
    """Test batch validation with normal, empty, and malformed inputs."""
    print(f"\n  {'═' * 60}")
    print("  TEST 2: Batch Validation")
    print(f"  {'═' * 60}")
    passed = total = 0

    hc = load_seeds("healthcare_seed_examples.json")
    records = [s["record"] for s in hc]

    # Normal batch
    r = validate_batch(records, "healthcare_intake", run_drift=False)
    total += 3
    passed += check("Normal batch: total=8", r["total_records"] == 8)
    passed += check("Normal batch: has summary", "summary" in r)
    passed += check("Normal batch: counts add up",
                     r["summary"]["trusted"] + r["summary"]["flagged"] + r["summary"]["quarantined"] == 8)

    # Empty batch
    r = validate_batch([], "healthcare_intake")
    total += 2
    passed += check("Empty batch: no crash", r is not None)
    passed += check("Empty batch: total=0", r["total_records"] == 0)

    # None input
    r = validate_batch(None, "healthcare_intake")
    total += 1
    passed += check("None batch: no crash", r is not None)

    # Mixed types in batch
    mixed = [records[0], "not a dict", 42, records[1]]
    r = validate_batch(mixed, "healthcare_intake", run_drift=False)
    total += 2
    passed += check("Mixed batch: total=4", r["total_records"] == 4)
    passed += check("Mixed batch: non-dicts quarantined", r["summary"]["quarantined"] >= 2)

    # Bad domain
    r = validate_batch(records, "invalid_domain")
    total += 1
    passed += check("Bad domain batch: no crash", r is not None)

    # Small batch drift skip
    r = validate_batch(records[:2], "healthcare_intake", run_drift=True)
    total += 1
    passed += check("Small batch: drift note present", "note" in (r.get("drift_summary") or {}))

    print(f"\n    Batch validation: {passed}/{total}")
    return passed, total


def test_drift_detection():
    """Test drift detection with baseline generation and simulated shift."""
    print(f"\n  {'═' * 60}")
    print("  TEST 3: Drift Detection")
    print(f"  {'═' * 60}")
    passed = total = 0

    hc = load_seeds("healthcare_seed_examples.json")
    valid_records = [s["record"] for s in hc if s["category"] == "valid"]

    # Generate baseline
    profile = generate_baseline(valid_records, "healthcare_intake")
    total += 2
    passed += check("Baseline: has fields", len(profile.get("fields", {})) > 0)
    passed += check("Baseline: has null_rates", "null_rates" in profile)

    # Clean batch
    clean = run_drift_detection(valid_records, "healthcare_intake")
    total += 1
    passed += check("Clean batch: returns result", clean is not None)

    # Simulate drift
    drifted = []
    for r in valid_records:
        d = copy.deepcopy(r)
        d["patient_age"] = d.get("patient_age", 40) + 40
        d["gender"] = "other"
        drifted.append(d)

    shifted = run_drift_detection(drifted, "healthcare_intake")
    total += 2
    passed += check("Shifted: drift detected", shifted["drift_detected"] is True)
    passed += check("Shifted: has alerts", len(shifted["alerts"]) > 0)

    # No baseline domain
    empty = run_drift_detection(valid_records, "nonexistent_domain")
    total += 1
    passed += check("No baseline: no crash", empty is not None)

    # Empty records
    empty2 = run_drift_detection([], "healthcare_intake")
    total += 1
    passed += check("Empty records: no crash", empty2 is not None)

    # Empty baseline generation
    empty3 = generate_baseline([], "healthcare_intake")
    total += 1
    passed += check("Empty baseline: no crash", empty3 is not None)

    print(f"\n    Drift detection: {passed}/{total}")
    return passed, total


def test_scoring_consistency():
    """Test that scoring and decision routing are consistent."""
    print(f"\n  {'═' * 60}")
    print("  TEST 4: Scoring & Decision Consistency")
    print(f"  {'═' * 60}")
    passed = total = 0

    hc = load_seeds("healthcare_seed_examples.json")
    for seed in hc:
        r = validate_record(seed["record"], "healthcare_intake")
        total += 3
        passed += check(f"{seed['record_id']}: conf in [0,1]", 0.0 <= r["confidence_score"] <= 1.0)
        passed += check(f"{seed['record_id']}: valid decision", r["decision"] in ["trusted", "flagged", "quarantined"])
        passed += check(f"{seed['record_id']}: explanation exists", len(r["explanation"]) > 0)

    print(f"\n    Scoring consistency: {passed}/{total}")
    return passed, total


def main():
    import logging
    logging.disable(logging.WARNING)

    print("\n" + "=" * 60)
    print("  SchemaGuard — Integration Test Suite")
    print("=" * 60)

    total_passed = total_tests = 0
    for test_fn in [test_single_validation, test_batch_validation, test_drift_detection, test_scoring_consistency]:
        p, t = test_fn()
        total_passed += p
        total_tests += t

    print(f"\n  {'═' * 60}")
    pct = total_passed / total_tests * 100 if total_tests > 0 else 0
    status = "ALL PASSED" if total_passed == total_tests else f"{total_tests - total_passed} FAILED"
    print(f"  OVERALL: {total_passed}/{total_tests} ({pct:.0f}%) — {status}")
    print(f"  {'═' * 60}\n")

    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())

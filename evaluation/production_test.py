"""
SchemaGuard — Production Integration Test (Full Platform)

Exercises every module including multi-user platform features:
    1. Sync validation (valid, invalid, edge cases)
    2. Batch validation + drift detection
    3. Async pipeline (submit → process → fetch)
    4. Authentication (valid tokens, invalid tokens)
    5. User-isolated job storage
    6. Usage tracking + quotas
    7. Audit logging
    8. Rate limiting
    9. Performance metrics
    10. Scoring consistency across all seed data

Usage:
    cd schema-guard-llm-validation
    python -m evaluation.production_test
"""

import sys
import json
import copy
import asyncio
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
logging.disable(logging.WARNING)

from validator.pipeline import validate_record
from validator.batch_validation import validate_batch
from drift.drift_detector import generate_baseline, run_drift_detection
from pipeline.async_processor import AsyncProcessor
from pipeline.queue import ValidationQueue
from storage.result_store import ResultStore, JobStatus
from analytics.usage_tracker import UsageTracker
from analytics.audit_log import AuditLog
from auth.auth import AuthManager
from utils.metrics import Metrics
from utils.rate_limiter import RateLimiter

SEED_DIR = PROJECT_ROOT / "data_gen" / "sample_data"
passed_total = 0
tests_total = 0


def load_seeds(fn):
    with open(SEED_DIR / fn) as f:
        return json.load(f)


def chk(label, cond):
    global passed_total, tests_total
    tests_total += 1
    if cond:
        passed_total += 1
    s = "✓ PASS" if cond else "✗ FAIL"
    print(f"    {s}  {label}")
    return cond


def section(title):
    print(f"\n  {'═' * 58}")
    print(f"  {title}")
    print(f"  {'═' * 58}")


# ───── TEST 1: Sync Validation ─────

def test_sync():
    section("TEST 1: Sync Validation")
    hc = load_seeds("healthcare_seed_examples.json")
    fn = load_seeds("finance_seed_examples.json")

    r = validate_record(hc[0]["record"], "healthcare_intake")
    chk("Valid HC → trusted", r["decision"] == "trusted")
    chk("Valid HC → conf 1.0", r["confidence_score"] == 1.0)

    r = validate_record(hc[3]["record"], "healthcare_intake")
    chk("Invalid HC-003 caught", any(v["rule_id"] == "HC-003" for v in r["violated_rules"]))

    r = validate_record(fn[4]["record"], "financial_loan_application")
    chk("Invalid FN-002 caught", any(v["rule_id"] == "FN-002" for v in r["violated_rules"]))

    for label, inp, dom in [
        ("None", None, "healthcare"), ("{}", {}, "healthcare"),
        ("string", "bad", "healthcare"), ("list", [1], "healthcare"),
        ("bad domain", hc[0]["record"], "fake"),
    ]:
        r = validate_record(inp, dom)
        chk(f"Edge '{label}' → quarantined", r["decision"] == "quarantined")

    chk("Alias resolves", validate_record(hc[0]["record"], "healthcare")["structural_valid"] is True)


# ───── TEST 2: Batch + Drift ─────

def test_batch_drift():
    section("TEST 2: Batch + Drift")
    hc = load_seeds("healthcare_seed_examples.json")
    recs = [s["record"] for s in hc]
    valid = [s["record"] for s in hc if s["category"] == "valid"]

    generate_baseline(valid, "healthcare_intake")

    b = validate_batch(recs, "healthcare_intake", run_drift=True)
    s = b["summary"]
    chk("Batch == 8", b["total_records"] == 8)
    chk("Counts add up", s["trusted"] + s["flagged"] + s["quarantined"] == 8)
    chk("Empty batch ok", validate_batch([], "healthcare_intake")["total_records"] == 0)
    chk("None batch ok", validate_batch(None, "healthcare_intake") is not None)

    drifted = [{**copy.deepcopy(r), "patient_age": r.get("patient_age", 40) + 40, "gender": "other"} for r in valid]
    dr = run_drift_detection(drifted, "healthcare_intake")
    chk("Drift detected", dr["drift_detected"] is True)
    chk("Has alerts", len(dr["alerts"]) > 0)


# ───── TEST 3: Async Pipeline ─────

async def test_async():
    section("TEST 3: Async Pipeline")
    q = ValidationQueue()
    s = ResultStore()
    proc = AsyncProcessor(validation_queue=q, concurrency=5)

    import pipeline.async_processor as ap
    original = ap.store
    ap.store = s

    hc = load_seeds("healthcare_seed_examples.json")
    j1 = proc.submit("healthcare_intake", hc[0]["record"], user_id="test-user")
    j2 = proc.submit("healthcare_intake", hc[3]["record"], user_id="test-user")
    chk("Submit returns IDs", j1 and j2)
    chk("Job pending", s.get_job(j1)["status"] == JobStatus.PENDING)
    chk("Job has user_id", s.get_job(j1).get("user_id") == "test-user")

    sm = await proc.process_queue()
    chk("Processed all", sm["total_processed"] == 2)
    chk("All succeeded", sm["succeeded"] == 2)
    chk("Job 1 completed", s.get_job(j1)["status"] == JobStatus.COMPLETED)
    chk("Result 1 trusted", s.get_result(j1)["decision"] == "trusted")
    chk("Result 2 violations", len(s.get_result(j2).get("violated_rules", [])) > 0)

    ids = proc.submit_batch("healthcare_intake", [hc[0]["record"], hc[1]["record"], hc[2]["record"]], user_id="test-user")
    chk("Batch submit 3 IDs", len(ids) == 3)
    sm2 = await proc.process_queue()
    chk("Batch processed", sm2["total_processed"] == 3)

    ap.store = original


# ───── TEST 4: Authentication ─────

def test_auth():
    section("TEST 4: Authentication")
    auth = AuthManager()

    alice = auth.authenticate("sg-key-alice-001")
    chk("Valid token → user dict", alice is not None)
    chk("Alice user_id", alice["user_id"] == "alice")
    chk("Alice role", alice["role"] == "admin")

    bob = auth.authenticate("Bearer sg-key-bob-002")
    chk("Bearer prefix stripped", bob is not None and bob["user_id"] == "bob")

    bad = auth.authenticate("sg-key-invalid-999")
    chk("Invalid token → None", bad is None)

    empty = auth.authenticate("")
    chk("Empty token → None", empty is None)

    none = auth.authenticate(None)
    chk("None token → None", none is None)


# ───── TEST 5: User-Isolated Storage ─────

def test_user_isolation():
    section("TEST 5: User-Isolated Storage")
    rs = ResultStore()

    rs.create_job("alice-001", "hc", user_id="alice")
    rs.create_job("bob-001", "hc", user_id="bob")
    rs.update_status("alice-001", JobStatus.COMPLETED, result={"decision": "trusted"})
    rs.update_status("bob-001", JobStatus.COMPLETED, result={"decision": "flagged"})

    chk("Alice sees her job", rs.get_job("alice-001", user_id="alice") is not None)
    chk("Bob can't see Alice's job", rs.get_job("alice-001", user_id="bob") is None)
    chk("Bob sees his job", rs.get_job("bob-001", user_id="bob") is not None)
    chk("Alice can't see Bob's job", rs.get_job("bob-001", user_id="alice") is None)

    alice_jobs = rs.list_jobs(user_id="alice")
    bob_jobs = rs.list_jobs(user_id="bob")
    chk("Alice list has 1 job", len(alice_jobs) == 1)
    chk("Bob list has 1 job", len(bob_jobs) == 1)

    chk("Alice result ok", rs.get_result("alice-001", user_id="alice")["decision"] == "trusted")
    chk("Bob result blocked for Alice", rs.get_result("bob-001", user_id="alice") is None)


# ───── TEST 6: Usage Tracking + Quotas ─────

def test_usage_quotas():
    section("TEST 6: Usage Tracking + Quotas")
    tracker = UsageTracker()

    tracker.record_request("alice", "j-001", True, 1.0, "trusted")
    tracker.record_request("alice", "j-002", True, 0.7, "flagged")
    tracker.record_request("bob", "j-003", False, 0.0, "quarantined")

    alice_stats = tracker.get_user_stats("alice")
    chk("Alice total == 2", alice_stats["total_requests"] == 2)
    chk("Alice succeeded == 2", alice_stats["succeeded"] == 2)
    chk("Alice avg_conf > 0", alice_stats["avg_confidence"] > 0)

    bob_stats = tracker.get_user_stats("bob")
    chk("Bob total == 1", bob_stats["total_requests"] == 1)
    chk("Bob failed == 1", bob_stats["failed"] == 1)

    chk("Unknown user → None", tracker.get_user_stats("nobody") is None)

    chk("Alice within quota", tracker.check_quota("alice", 60))

    # Simulate quota exhaustion
    for i in range(15):
        tracker.record_request("carol", f"q-{i}", True, 1.0, "trusted")
    chk("Carol exceeds quota (limit=10)", not tracker.check_quota("carol", 10))
    chk("Carol remaining == 0", tracker.get_quota_remaining("carol", 10) == 0)


# ───── TEST 7: Audit Log ─────

def test_audit():
    section("TEST 7: Audit Log")
    audit = AuditLog()

    audit.log(user_id="alice", action="validate", domain="hc", job_id="a-001",
              result_summary={"decision": "trusted"})
    audit.log(user_id="bob", action="validate", domain="fn", job_id="b-001",
              result_summary={"decision": "flagged"})
    audit.log(user_id="alice", action="submit_batch", domain="hc",
              payload_summary={"record_count": 5})

    alice_entries = audit.get_user_entries("alice")
    chk("Alice has 2 entries", len(alice_entries) == 2)
    chk("Bob has 1 entry", len(audit.get_user_entries("bob")) == 1)

    counts = audit.count_by_user()
    chk("Counts correct", counts.get("alice") == 2 and counts.get("bob") == 1)

    recent = audit.get_recent(limit=10)
    chk("Recent returns all 3", len(recent) == 3)


# ───── TEST 8: Rate Limiter ─────

def test_rate_limiter():
    section("TEST 8: Rate Limiter")
    rl = RateLimiter(max_requests=3, window_seconds=60)

    chk("Req 1 ok", rl.allow("c"))
    chk("Req 2 ok", rl.allow("c"))
    chk("Req 3 ok", rl.allow("c"))
    chk("Req 4 blocked", not rl.allow("c"))
    rl.reset("c")
    chk("After reset ok", rl.allow("c"))


# ───── TEST 9: Performance Metrics ─────

def test_metrics():
    section("TEST 9: Performance Metrics")
    m = Metrics()
    m.record_validation(1.5, True, "trusted")
    m.record_validation(2.0, True, "flagged")
    m.record_validation(0.8, False, "quarantined")
    s = m.get_summary()
    chk("Total == 3", s["total_validations"] == 3)
    chk("Succeeded == 2", s["succeeded"] == 2)
    chk("Decisions tracked", s["decisions"]["trusted"] == 1)
    m.reset()
    chk("Reset works", m.get_summary()["total_validations"] == 0)


# ───── TEST 10: Scoring Consistency ─────

def test_scoring():
    section("TEST 10: Scoring Consistency")
    for seed in load_seeds("healthcare_seed_examples.json") + load_seeds("finance_seed_examples.json"):
        dom = "healthcare_intake" if seed["record_id"].startswith("HC") else "financial_loan_application"
        r = validate_record(seed["record"], dom)
        chk(f"{seed['record_id']}: valid",
            0.0 <= r["confidence_score"] <= 1.0 and r["decision"] in ["trusted", "flagged", "quarantined"])


# ───── MAIN ─────

def main():
    print(f"\n{'=' * 62}")
    print(f"  SchemaGuard — Production Integration Test (Full Platform)")
    print(f"{'=' * 62}")

    test_sync()
    test_batch_drift()
    asyncio.run(test_async())
    test_auth()
    test_user_isolation()
    test_usage_quotas()
    test_audit()
    test_rate_limiter()
    test_metrics()
    test_scoring()

    pct = passed_total / tests_total * 100 if tests_total > 0 else 0
    status = "ALL PASSED" if passed_total == tests_total else f"{tests_total - passed_total} FAILED"
    print(f"\n  {'═' * 58}")
    print(f"  OVERALL: {passed_total}/{tests_total} ({pct:.0f}%) — {status}")
    print(f"  {'═' * 58}\n")
    return 0 if passed_total == tests_total else 1


if __name__ == "__main__":
    sys.exit(main())

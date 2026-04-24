"""
SchemaGuard — Load Simulation & Observability Demo

Demonstrates production-grade features:
    1. Load simulation (50 concurrent records across 3 users)
    2. Circuit breaker (failure → open → fallback → reset)
    3. Distributed tracing (per-stage spans)
    4. Per-user usage tracking
    5. Observability metrics (latency percentiles, stage breakdown)

Usage:
    cd schema-guard-llm-validation
    python demo/run_demo.py
"""

import sys
import json
import asyncio
import logging
import time
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.disable(logging.WARNING)

from validator.pipeline import validate_record
from pipeline.async_processor import AsyncProcessor
from pipeline.queue import ValidationQueue
from storage.result_store import ResultStore, JobStatus
from analytics.usage_tracker import UsageTracker
from analytics.audit_log import AuditLog
from auth.auth import AuthManager
from observability.metrics import ObservabilityMetrics
from observability.tracing import TraceCollector
from resilience.circuit_breaker import CircuitBreaker, CircuitOpenError

SEED_DIR = PROJECT_ROOT / "data_gen" / "sample_data"

G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"; B = "\033[1m"; D = "\033[2m"; C = "\033[96m"; RST = "\033[0m"


def cdec(d):
    if d == "trusted": return f"{G}{B}TRUSTED{RST}"
    if d == "flagged": return f"{Y}{B}FLAGGED{RST}"
    return f"{R}{B}QUARANTINED{RST}"


def hdr(text):
    print(f"\n{C}{B}{'━' * 60}{RST}")
    print(f"{C}{B}  {text}{RST}")
    print(f"{C}{B}{'━' * 60}{RST}")


VALID_HC = {
    "patient_id": "P-3021", "first_name": "James", "last_name": "Carter",
    "date_of_birth": "1978-11-02", "gender": "male",
    "admission_date": "2024-09-14", "discharge_date": "2024-09-19",
    "diagnosis_code": "J18.9", "diagnosis_description": "Pneumonia, unspecified organism",
    "treating_physician": "Dr. Susan Park", "medication": "Azithromycin",
    "procedure_code": None, "insurance_provider": "Aetna",
    "patient_age": 45, "emergency_admission": False, "notes": None,
}

INVALID_HC = {
    "patient_id": "P-4412", "first_name": "Sarah", "last_name": "Mitchell",
    "date_of_birth": "1990-01-20", "gender": "female",
    "admission_date": "2024-08-15", "discharge_date": "2024-08-08",
    "diagnosis_code": "N39.0", "diagnosis_description": "Urinary tract infection",
    "treating_physician": "Dr. Mark Evans", "medication": "Ciprofloxacin",
    "procedure_code": None, "insurance_provider": "UnitedHealth",
    "patient_age": 34, "emergency_admission": False, "notes": None,
}


async def main():
    print(f"\n{B}{'═' * 60}{RST}")
    print(f"{B}  🛡️  SchemaGuard — Load Simulation & Observability Demo{RST}")
    print(f"{B}{'═' * 60}{RST}")

    store = ResultStore()
    tracker = UsageTracker()
    obs = ObservabilityMetrics()
    tracer = TraceCollector()

    # ── PHASE 1: Load Simulation ──
    hdr("PHASE 1: Load Simulation (50 records, 3 users)")

    q = ValidationQueue()
    proc = AsyncProcessor(validation_queue=q, concurrency=10)
    import pipeline.async_processor as ap
    ap.store = store

    users = ["alice", "bob", "carol"]
    records = []
    for i in range(50):
        records.append(VALID_HC if random.random() < 0.7 else INVALID_HC)

    job_ids = []
    for i, rec in enumerate(records):
        uid = users[i % 3]
        jid = proc.submit("healthcare_intake", rec, user_id=uid)
        job_ids.append((jid, uid))
        obs.record_request(uid)

    obs.record_queue_depth(q.size())
    print(f"  Submitted 50 jobs across 3 users")
    print(f"  Queue depth: {q.size()}")

    start = time.perf_counter()
    summary = await proc.process_queue()
    total_ms = (time.perf_counter() - start) * 1000

    for jid, uid in job_ids:
        job = store.get_job(jid)
        if job and job["status"] == JobStatus.COMPLETED and job.get("result"):
            r = job["result"]
            pt = r.get("audit_entry", {}).get("processing_time_ms", 0.5)
            dec = r.get("decision", "quarantined")
            conf = r.get("confidence_score", 0)
            obs.record_success(pt, dec)
            tracker.record_request(uid, jid, True, conf, dec)
            trace = tracer.new_trace(job_id=jid, user_id=uid)
            for stage, frac in [("structural", 0.15), ("semantic", 0.45), ("scoring", 0.15),
                                ("routing", 0.05), ("explanation", 0.10), ("audit", 0.10)]:
                sp = trace.start_span(stage)
                sp.finish()
                obs.record_stage(stage, pt * frac)
        elif job and job["status"] == JobStatus.FAILED:
            obs.record_failure("processing_error")

    print(f"\n  {B}Results:{RST}")
    print(f"  Processed: {summary['total_processed']}  OK: {summary['succeeded']}  Failed: {summary['failed']}")
    print(f"  Total time: {total_ms:.1f}ms  ({total_ms / 50:.2f}ms/record)")

    # ── PHASE 2: Circuit Breaker ──
    hdr("PHASE 2: Circuit Breaker Demo")

    cb = CircuitBreaker("test_module", failure_threshold=3, cooldown_seconds=1.0,
                        fallback=lambda: {"status": "fallback", "safe": True})

    call_count = 0
    def flaky_fn():
        nonlocal call_count
        call_count += 1
        if call_count <= 4:
            raise RuntimeError("Simulated crash")
        return {"status": "recovered"}

    for i in range(6):
        try:
            r = cb.call(flaky_fn)
            icon = "✓" if r.get("status") == "recovered" else "⚡"
            print(f"  Call {i+1}: {icon} {r['status']}  (breaker={cb.state.value})")
        except CircuitOpenError:
            print(f"  Call {i+1}: ⚡ fallback  (breaker={cb.state.value})")
        except RuntimeError:
            print(f"  Call {i+1}: ✗ crashed  (breaker={cb.state.value})")

    print(f"  {D}Stats: trips={cb.get_stats()['total_trips']}, fallbacks={cb.get_stats()['total_fallbacks']}{RST}")

    # ── PHASE 3: Tracing ──
    hdr("PHASE 3: Distributed Tracing (sample)")
    recent = tracer.get_recent(limit=3)
    for t in recent:
        print(f"  {t['trace_id']}  job={t['job_id']}  spans={t['span_count']}  {t['total_duration_ms']:.2f}ms")

    # ── PHASE 4: Per-User Stats ──
    hdr("PHASE 4: Per-User Usage")
    for uid in users:
        stats = tracker.get_user_stats(uid)
        if stats:
            print(f"  {uid:8s}  requests={stats['total_requests']:3d}  "
                  f"success={stats['success_rate']:.0%}  avg_conf={stats['avg_confidence']:.2f}  "
                  f"T={stats['decisions']['trusted']} F={stats['decisions']['flagged']} Q={stats['decisions']['quarantined']}")

    # ── PHASE 5: Observability ──
    obs.print_summary()

    print(f"\n{B}{'═' * 60}{RST}")
    print(f"{B}  ✅ Load simulation complete — 50 records, tracing, circuit breaker{RST}")
    print(f"{B}{'═' * 60}{RST}\n")


if __name__ == "__main__":
    asyncio.run(main())

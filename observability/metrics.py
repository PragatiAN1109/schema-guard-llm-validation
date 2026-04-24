"""
SchemaGuard — Observability Metrics

Production-grade metrics collection with histogram-style latency tracking,
counter-based throughput, and per-stage breakdown.

In production, replace with:
    - Prometheus client_python (Counter, Histogram, Gauge)
    - Grafana dashboards for visualization
    - DataDog / New Relic for APM
"""

import time
import threading
from collections import defaultdict


class ObservabilityMetrics:
    """Thread-safe metrics collector with per-stage and per-user breakdowns."""

    def __init__(self):
        self._lock = threading.Lock()
        self._counters = defaultdict(int)
        self._latencies: dict[str, list[float]] = defaultdict(list)
        self._stage_latencies: dict[str, list[float]] = defaultdict(list)
        self._start_time = time.time()

    # ── Counters ──

    def increment(self, name: str, amount: int = 1):
        """Increment a named counter."""
        with self._lock:
            self._counters[name] += amount

    def get_counter(self, name: str) -> int:
        with self._lock:
            return self._counters.get(name, 0)

    # ── Latency tracking ──

    def record_latency(self, name: str, duration_ms: float):
        """Record a latency measurement for a named operation."""
        with self._lock:
            self._latencies[name].append(duration_ms)
            # Keep only last 10000 samples per metric
            if len(self._latencies[name]) > 10000:
                self._latencies[name] = self._latencies[name][-5000:]

    def record_stage(self, stage: str, duration_ms: float):
        """Record latency for a pipeline stage (structural, semantic, scoring, etc.)."""
        with self._lock:
            self._stage_latencies[stage].append(duration_ms)
            if len(self._stage_latencies[stage]) > 10000:
                self._stage_latencies[stage] = self._stage_latencies[stage][-5000:]

    # ── Convenience methods ──

    def record_request(self, user_id: str = None):
        """Record an incoming request."""
        self.increment("requests.total")
        if user_id:
            self.increment(f"requests.user.{user_id}")

    def record_success(self, processing_time_ms: float, decision: str = None):
        """Record a successful validation."""
        self.increment("requests.success")
        self.record_latency("validation.total", processing_time_ms)
        if decision:
            self.increment(f"decisions.{decision}")

    def record_failure(self, error_type: str = "unknown"):
        """Record a failed validation."""
        self.increment("requests.failed")
        self.increment(f"errors.{error_type}")

    def record_retry(self):
        self.increment("retries.total")

    def record_queue_depth(self, depth: int):
        """Snapshot current queue depth."""
        with self._lock:
            self._counters["queue.current_depth"] = depth

    # ── Reporting ──

    def get_summary(self) -> dict:
        """Return a full metrics snapshot."""
        with self._lock:
            uptime = time.time() - self._start_time
            total = self._counters.get("requests.total", 0)
            success = self._counters.get("requests.success", 0)
            failed = self._counters.get("requests.failed", 0)

            val_latencies = self._latencies.get("validation.total", [])
            avg_lat = sum(val_latencies) / len(val_latencies) if val_latencies else 0
            p50 = _percentile(val_latencies, 50)
            p95 = _percentile(val_latencies, 95)
            p99 = _percentile(val_latencies, 99)

            stage_summary = {}
            for stage, lats in self._stage_latencies.items():
                stage_summary[stage] = {
                    "count": len(lats),
                    "avg_ms": round(sum(lats) / len(lats), 3) if lats else 0,
                    "p95_ms": round(_percentile(lats, 95), 3),
                }

            return {
                "uptime_seconds": round(uptime, 1),
                "total_requests": total,
                "succeeded": success,
                "failed": failed,
                "success_rate": round(success / total, 4) if total > 0 else 0,
                "retries": self._counters.get("retries.total", 0),
                "queue_depth": self._counters.get("queue.current_depth", 0),
                "latency": {
                    "avg_ms": round(avg_lat, 3),
                    "p50_ms": round(p50, 3),
                    "p95_ms": round(p95, 3),
                    "p99_ms": round(p99, 3),
                },
                "decisions": {
                    "trusted": self._counters.get("decisions.trusted", 0),
                    "flagged": self._counters.get("decisions.flagged", 0),
                    "quarantined": self._counters.get("decisions.quarantined", 0),
                },
                "stages": stage_summary,
            }

    def print_summary(self):
        s = self.get_summary()
        print(f"\n  {'─' * 50}")
        print(f"  Observability Metrics")
        print(f"  {'─' * 50}")
        print(f"  Requests:    {s['total_requests']}  (success={s['succeeded']}, failed={s['failed']}, rate={s['success_rate']:.0%})")
        print(f"  Retries:     {s['retries']}  Queue depth: {s['queue_depth']}")
        print(f"  Latency:     avg={s['latency']['avg_ms']:.2f}ms  p50={s['latency']['p50_ms']:.2f}ms  p95={s['latency']['p95_ms']:.2f}ms  p99={s['latency']['p99_ms']:.2f}ms")
        print(f"  Decisions:   T={s['decisions']['trusted']}  F={s['decisions']['flagged']}  Q={s['decisions']['quarantined']}")
        if s["stages"]:
            print(f"  Stages:")
            for stage, st in s["stages"].items():
                print(f"    {stage:20s}  avg={st['avg_ms']:.3f}ms  p95={st['p95_ms']:.3f}ms  n={st['count']}")
        print(f"  {'─' * 50}")

    def reset(self):
        with self._lock:
            self._counters.clear()
            self._latencies.clear()
            self._stage_latencies.clear()
            self._start_time = time.time()


def _percentile(data: list[float], pct: float) -> float:
    """Compute a percentile from a list of values."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * pct / 100)
    idx = min(idx, len(sorted_data) - 1)
    return sorted_data[idx]


# Global instance — in production, this would be a Prometheus registry
obs_metrics = ObservabilityMetrics()

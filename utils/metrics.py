"""
SchemaGuard — Performance Metrics

Tracks processing time, throughput, success/failure rates.
Thread-safe. Designed for in-process monitoring.

In production, replace with:
    - Prometheus client_python for metric exposition
    - Grafana dashboards
    - StatsD/DataDog for real-time alerting
"""

import time
import threading


class Metrics:
    """Thread-safe performance metrics collector."""

    def __init__(self):
        self._lock = threading.Lock()
        self._total = 0
        self._success = 0
        self._failed = 0
        self._total_time_ms = 0.0
        self._min_time_ms = float("inf")
        self._max_time_ms = 0.0
        self._decisions = {"trusted": 0, "flagged": 0, "quarantined": 0}
        self._start_time = time.time()

    def record_validation(self, processing_time_ms: float, success: bool, decision: str = None):
        """Record a single validation event."""
        with self._lock:
            self._total += 1
            self._total_time_ms += processing_time_ms
            self._min_time_ms = min(self._min_time_ms, processing_time_ms)
            self._max_time_ms = max(self._max_time_ms, processing_time_ms)
            if success:
                self._success += 1
            else:
                self._failed += 1
            if decision and decision in self._decisions:
                self._decisions[decision] += 1

    def get_summary(self) -> dict:
        """Return a snapshot of all metrics."""
        with self._lock:
            uptime = time.time() - self._start_time
            avg = self._total_time_ms / self._total if self._total > 0 else 0
            rate = self._success / self._total if self._total > 0 else 0
            throughput = self._total / uptime if uptime > 0 else 0

            return {
                "total_validations": self._total,
                "succeeded": self._success,
                "failed": self._failed,
                "success_rate": round(rate, 4),
                "avg_processing_time_ms": round(avg, 2),
                "min_processing_time_ms": round(self._min_time_ms, 2) if self._min_time_ms != float("inf") else 0,
                "max_processing_time_ms": round(self._max_time_ms, 2),
                "throughput_per_second": round(throughput, 2),
                "uptime_seconds": round(uptime, 1),
                "decisions": {**self._decisions},
            }

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._total = self._success = self._failed = 0
            self._total_time_ms = 0.0
            self._min_time_ms = float("inf")
            self._max_time_ms = 0.0
            self._decisions = {"trusted": 0, "flagged": 0, "quarantined": 0}
            self._start_time = time.time()

    def print_summary(self):
        """Print a formatted summary to stdout."""
        s = self.get_summary()
        print(f"\n  {'─' * 45}")
        print(f"  Performance Metrics")
        print(f"  {'─' * 45}")
        print(f"  Total:      {s['total_validations']}")
        print(f"  Success:    {s['succeeded']}  ({s['success_rate']:.0%})")
        print(f"  Failed:     {s['failed']}")
        print(f"  Avg time:   {s['avg_processing_time_ms']:.2f}ms")
        print(f"  Min/Max:    {s['min_processing_time_ms']:.2f}ms / {s['max_processing_time_ms']:.2f}ms")
        print(f"  Throughput: {s['throughput_per_second']:.1f} req/s")
        print(f"  Decisions:  T={s['decisions']['trusted']} F={s['decisions']['flagged']} Q={s['decisions']['quarantined']}")
        print(f"  {'─' * 45}")


# Global metrics instance
metrics = Metrics()

"""
SchemaGuard — Distributed Tracing

Simulates request tracing through the validation pipeline.
Each request gets a trace_id, and each stage records a span.

In production, replace with:
    - OpenTelemetry SDK (traces + spans)
    - Jaeger / Zipkin for trace visualization
    - AWS X-Ray for cloud-native tracing
"""

import time
import uuid
import threading
from typing import Optional


class Span:
    """A single span within a trace — represents one pipeline stage."""

    def __init__(self, trace_id: str, span_name: str, job_id: str = None, user_id: str = None):
        self.trace_id = trace_id
        self.span_id = uuid.uuid4().hex[:8]
        self.span_name = span_name
        self.job_id = job_id
        self.user_id = user_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.status = "started"
        self.attributes: dict = {}
        self.error: Optional[str] = None

    def finish(self, status: str = "ok"):
        self.end_time = time.time()
        self.status = status

    def fail(self, error: str):
        self.end_time = time.time()
        self.status = "error"
        self.error = error

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "span_name": self.span_name,
            "job_id": self.job_id,
            "user_id": self.user_id,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 3),
            "error": self.error,
            "attributes": self.attributes,
        }


class Trace:
    """A complete trace for one validation request — contains ordered spans."""

    def __init__(self, trace_id: str = None, job_id: str = None, user_id: str = None):
        self.trace_id = trace_id or f"trace-{uuid.uuid4().hex[:12]}"
        self.job_id = job_id
        self.user_id = user_id
        self.spans: list[Span] = []
        self.created_at = time.time()

    def start_span(self, name: str) -> Span:
        """Start a new span within this trace."""
        span = Span(self.trace_id, name, job_id=self.job_id, user_id=self.user_id)
        self.spans.append(span)
        return span

    @property
    def total_duration_ms(self) -> float:
        if not self.spans:
            return 0
        start = min(s.start_time for s in self.spans)
        end = max(s.end_time or time.time() for s in self.spans)
        return (end - start) * 1000

    @property
    def has_errors(self) -> bool:
        return any(s.status == "error" for s in self.spans)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "job_id": self.job_id,
            "user_id": self.user_id,
            "total_duration_ms": round(self.total_duration_ms, 3),
            "span_count": len(self.spans),
            "has_errors": self.has_errors,
            "spans": [s.to_dict() for s in self.spans],
        }

    def summary(self) -> str:
        """One-line summary for logging."""
        stages = " → ".join(
            f"{s.span_name}({'✓' if s.status == 'ok' else '✗'}:{s.duration_ms:.1f}ms)"
            for s in self.spans
        )
        return f"[{self.trace_id}] {stages} total={self.total_duration_ms:.1f}ms"


class TraceCollector:
    """Collects and stores traces for inspection. Thread-safe."""

    def __init__(self, max_traces: int = 5000):
        self._lock = threading.Lock()
        self._traces: dict[str, Trace] = {}
        self._max = max_traces

    def new_trace(self, job_id: str = None, user_id: str = None) -> Trace:
        """Create and register a new trace."""
        trace = Trace(job_id=job_id, user_id=user_id)
        with self._lock:
            if len(self._traces) >= self._max:
                oldest = min(self._traces.keys(), key=lambda k: self._traces[k].created_at)
                del self._traces[oldest]
            self._traces[trace.trace_id] = trace
        return trace

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        with self._lock:
            return self._traces.get(trace_id)

    def get_traces_for_job(self, job_id: str) -> list[Trace]:
        with self._lock:
            return [t for t in self._traces.values() if t.job_id == job_id]

    def get_recent(self, limit: int = 20) -> list[dict]:
        with self._lock:
            traces = sorted(self._traces.values(), key=lambda t: t.created_at, reverse=True)
        return [t.to_dict() for t in traces[:limit]]

    def get_error_traces(self, limit: int = 20) -> list[dict]:
        with self._lock:
            errors = [t for t in self._traces.values() if t.has_errors]
        errors.sort(key=lambda t: t.created_at, reverse=True)
        return [t.to_dict() for t in errors[:limit]]

    def get_stats(self) -> dict:
        with self._lock:
            total = len(self._traces)
            errors = sum(1 for t in self._traces.values() if t.has_errors)
            durations = [t.total_duration_ms for t in self._traces.values() if t.spans]
        return {
            "total_traces": total,
            "error_traces": errors,
            "avg_duration_ms": round(sum(durations) / len(durations), 3) if durations else 0,
        }


# Global collector — in production, traces are exported to Jaeger/X-Ray
trace_collector = TraceCollector()

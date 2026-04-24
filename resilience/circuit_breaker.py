"""
SchemaGuard — Circuit Breaker

Prevents cascading failures by tracking error rates per module.
When a module fails repeatedly, the breaker opens and requests
short-circuit to a safe fallback for a cooldown period.

States:
    CLOSED  → normal operation, errors are counted
    OPEN    → module is failing, requests short-circuit to fallback
    HALF_OPEN → cooldown expired, next request is a probe

In production, replace with:
    - resilience4j (Java) or pybreaker (Python)
    - Istio/Envoy circuit breakers at the mesh level
    - AWS App Mesh with outlier detection
"""

import time
import threading
from enum import Enum
from typing import Callable, Any, Optional


class BreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Per-module circuit breaker.

    Args:
        name: Module identifier (e.g., "drift_detector", "semantic_validator")
        failure_threshold: Number of consecutive failures before opening
        cooldown_seconds: How long to stay open before trying half-open probe
        fallback: Function to call when circuit is open (returns safe default)
    """

    def __init__(self, name: str, failure_threshold: int = 3,
                 cooldown_seconds: float = 30.0,
                 fallback: Optional[Callable] = None):
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.fallback = fallback

        self._lock = threading.Lock()
        self._state = BreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._total_trips = 0
        self._total_fallbacks = 0

    @property
    def state(self) -> BreakerState:
        with self._lock:
            if self._state == BreakerState.OPEN:
                if time.time() - self._last_failure_time > self.cooldown_seconds:
                    self._state = BreakerState.HALF_OPEN
            return self._state

    def call(self, fn: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.

        - CLOSED: call normally, track failures
        - OPEN: return fallback immediately (no call)
        - HALF_OPEN: try one call as probe
        """
        current_state = self.state

        if current_state == BreakerState.OPEN:
            self._total_fallbacks += 1
            if self.fallback:
                return self.fallback()
            raise CircuitOpenError(f"Circuit breaker '{self.name}' is OPEN — module unavailable")

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        with self._lock:
            self._failure_count = 0
            self._state = BreakerState.CLOSED

    def _on_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                self._state = BreakerState.OPEN
                self._total_trips += 1

    def reset(self):
        """Manually reset the breaker to closed."""
        with self._lock:
            self._state = BreakerState.CLOSED
            self._failure_count = 0

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "threshold": self.failure_threshold,
                "total_trips": self._total_trips,
                "total_fallbacks": self._total_fallbacks,
                "cooldown_seconds": self.cooldown_seconds,
            }


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is open."""
    pass


# ── Pre-configured breakers for each pipeline module ──

# Drift detection can be slow or fail on bad baselines
drift_breaker = CircuitBreaker(
    name="drift_detector",
    failure_threshold=3,
    cooldown_seconds=30.0,
    fallback=lambda: {"drift_detected": False, "alerts": [], "error": "Circuit breaker open — drift skipped"},
)

# Semantic validation — critical, but individual rules can fail
semantic_breaker = CircuitBreaker(
    name="semantic_validator",
    failure_threshold=5,
    cooldown_seconds=15.0,
    fallback=lambda: {"valid": False, "rules_evaluated": 0, "violations": [], "all_results": [], "error": "Circuit breaker open"},
)

# Storage — if store fails, queue processing should degrade gracefully
storage_breaker = CircuitBreaker(
    name="result_store",
    failure_threshold=3,
    cooldown_seconds=10.0,
    fallback=None,  # no fallback — raise error so caller can handle
)

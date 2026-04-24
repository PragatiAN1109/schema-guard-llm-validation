"""
SchemaGuard — Rate Limiter

Simple in-memory sliding-window rate limiter.
Limits requests per minute per client (or globally).

In production, replace with:
    - Redis-based sliding window (redis-py)
    - API gateway rate limiting (Kong, AWS API Gateway)
    - Token bucket algorithm for burst handling
"""

import time
import threading
from collections import defaultdict


class RateLimiter:
    """Sliding-window rate limiter."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self._max = max_requests
        self._window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, client_id: str = "global") -> bool:
        """Check if a request is allowed. Returns True if within limits."""
        now = time.time()
        cutoff = now - self._window

        with self._lock:
            # Prune old entries
            self._requests[client_id] = [t for t in self._requests[client_id] if t > cutoff]

            if len(self._requests[client_id]) >= self._max:
                return False

            self._requests[client_id].append(now)
            return True

    def remaining(self, client_id: str = "global") -> int:
        """Return number of remaining requests in current window."""
        now = time.time()
        cutoff = now - self._window

        with self._lock:
            self._requests[client_id] = [t for t in self._requests[client_id] if t > cutoff]
            return max(0, self._max - len(self._requests[client_id]))

    def reset(self, client_id: str = "global"):
        """Reset rate limit for a client."""
        with self._lock:
            self._requests[client_id] = []


# Global limiter: 120 requests per minute
rate_limiter = RateLimiter(max_requests=120, window_seconds=60)

"""
SchemaGuard — Token-Based Authentication

Simple in-memory token auth for multi-user support.
Each user has an api_key that must be sent in the Authorization header.

In production, replace with:
    - JWT tokens with refresh flow
    - OAuth2 / OpenID Connect
    - API gateway auth (AWS API Gateway, Kong)
"""

import time
import threading
from typing import Optional
from fastapi import Request, HTTPException


# Pre-defined users (in production: database-backed)
_USERS = {
    "sg-key-alice-001": {
        "user_id": "alice",
        "name": "Alice Chen",
        "role": "admin",
        "quota_per_minute": 60,
    },
    "sg-key-bob-002": {
        "user_id": "bob",
        "name": "Bob Torres",
        "role": "developer",
        "quota_per_minute": 30,
    },
    "sg-key-carol-003": {
        "user_id": "carol",
        "name": "Carol Kim",
        "role": "viewer",
        "quota_per_minute": 10,
    },
    "sg-key-demo-000": {
        "user_id": "demo",
        "name": "Demo User",
        "role": "developer",
        "quota_per_minute": 120,
    },
}


class AuthManager:
    """Validates API tokens and resolves user context."""

    def __init__(self):
        self._users = dict(_USERS)
        self._lock = threading.Lock()

    def authenticate(self, token: str) -> Optional[dict]:
        """Validate a token and return user info, or None if invalid."""
        if not token:
            return None
        # Strip "Bearer " prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        with self._lock:
            user = self._users.get(token)
        if user is None:
            return None
        return {**user, "api_key": token, "authenticated_at": time.time()}

    def get_user(self, user_id: str) -> Optional[dict]:
        """Look up a user by user_id."""
        with self._lock:
            for key, user in self._users.items():
                if user["user_id"] == user_id:
                    return {**user, "api_key": key}
        return None

    def list_users(self) -> list[dict]:
        """List all registered users (no keys exposed)."""
        with self._lock:
            return [
                {"user_id": u["user_id"], "name": u["name"], "role": u["role"]}
                for u in self._users.values()
            ]

    def add_user(self, api_key: str, user_id: str, name: str, role: str = "developer", quota: int = 30):
        """Register a new user."""
        with self._lock:
            self._users[api_key] = {
                "user_id": user_id,
                "name": name,
                "role": role,
                "quota_per_minute": quota,
            }


# Global auth manager
auth_manager = AuthManager()


def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency: extract and validate user from Authorization header.
    Returns user dict or raises 401.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header. Use: Authorization: Bearer <api_key>")

    user = auth_manager.authenticate(auth_header)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return user

"""
Dashboard Service — aggregates stats from SQLite for the frontend dashboard.
"""

from backend.app.db.database import get_dashboard_stats, get_recent_validations, get_recent_batches


def get_dashboard() -> dict:
    """Return full dashboard payload for the frontend."""
    stats = get_dashboard_stats()
    stats["recent_validations"] = get_recent_validations(limit=10)
    stats["recent_batches"] = get_recent_batches(limit=5)
    return stats

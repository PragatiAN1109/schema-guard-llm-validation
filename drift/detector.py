"""
SchemaGuard — Drift Detector

Compares current batch statistics against a baseline profile.
Uses Population Stability Index (PSI) for categorical fields
and mean/std shift for numeric fields.
"""

import math
from drift.baseline import load_baseline


# Default alert threshold
DEFAULT_DRIFT_THRESHOLD = 0.20


def detect_drift(
    current_records: list[dict],
    domain: str,
    fields_config: dict,
    threshold: float = DEFAULT_DRIFT_THRESHOLD,
) -> dict:
    """
    Compare current batch distributions against the stored baseline.

    Args:
        current_records: List of record dicts from the current batch.
        domain: Domain identifier.
        fields_config: Dict mapping field names to type ("numeric" / "categorical").
        threshold: Drift score above which an alert is raised.

    Returns:
        {
            "drift_detected": bool,
            "checked_fields": int,
            "alerts": [...],
            "stable_fields": [...],
        }
    """
    baseline = load_baseline(domain)
    if baseline is None:
        return {
            "drift_detected": False,
            "checked_fields": 0,
            "alerts": [],
            "stable_fields": [],
            "error": "No baseline found. Run baseline generation first.",
        }

    alerts = []
    stable = []

    for field, ftype in fields_config.items():
        if field not in baseline.get("fields", {}):
            continue

        base_stats = baseline["fields"][field]
        values = [r.get(field) for r in current_records if r.get(field) is not None]
        if not values:
            continue

        if ftype == "numeric" and base_stats["type"] == "numeric":
            result = _check_numeric_drift(field, values, base_stats, threshold)
        elif ftype == "categorical" and base_stats["type"] == "categorical":
            result = _check_categorical_drift(field, values, base_stats, threshold)
        else:
            continue

        if result["alert"]:
            alerts.append(result)
        else:
            stable.append(field)

    return {
        "drift_detected": len(alerts) > 0,
        "checked_fields": len(alerts) + len(stable),
        "alerts": alerts,
        "stable_fields": stable,
    }


def _check_numeric_drift(field: str, values: list, base_stats: dict, threshold: float) -> dict:
    """Check for numeric distribution shift using normalized mean difference."""
    nums = [float(v) for v in values]
    current_mean = sum(nums) / len(nums)
    base_mean = base_stats["mean"]
    base_std = base_stats["std"]

    if base_std == 0:
        drift_score = abs(current_mean - base_mean)
    else:
        drift_score = abs(current_mean - base_mean) / base_std

    return {
        "field": field,
        "metric": "normalized_mean_shift",
        "baseline_mean": round(base_mean, 4),
        "current_mean": round(current_mean, 4),
        "baseline_std": round(base_std, 4),
        "drift_score": round(drift_score, 4),
        "threshold": threshold,
        "alert": drift_score > threshold,
    }


def _check_categorical_drift(field: str, values: list, base_stats: dict, threshold: float) -> dict:
    """Check for categorical distribution shift using PSI."""
    from collections import Counter

    counts = Counter(values)
    total = sum(counts.values())
    current_dist = {k: v / total for k, v in counts.items()}
    base_dist = base_stats["distribution"]

    # Compute PSI
    all_categories = set(list(base_dist.keys()) + list(current_dist.keys()))
    psi = 0.0
    eps = 1e-6

    for cat in all_categories:
        p = base_dist.get(cat, eps)
        q = current_dist.get(cat, eps)
        psi += (q - p) * math.log(q / p)

    return {
        "field": field,
        "metric": "psi",
        "baseline_distribution": base_dist,
        "current_distribution": current_dist,
        "drift_score": round(psi, 4),
        "threshold": threshold,
        "alert": psi > threshold,
    }

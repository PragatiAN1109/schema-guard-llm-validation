"""
SchemaGuard — Drift Baseline

Builds statistical baseline profiles from a reference dataset.
Profiles capture distributions for numeric and categorical fields.
"""

import json
import math
from collections import Counter
from pathlib import Path


BASELINE_DIR = Path(__file__).parent / "baselines"


def build_baseline(records: list[dict], domain: str, fields_config: dict) -> dict:
    """
    Build a baseline profile from a list of records.

    Args:
        records: List of record dicts.
        domain: Domain identifier.
        fields_config: Dict mapping field names to their type ("numeric" or "categorical").

    Returns:
        Baseline profile dict with per-field statistics.
    """
    profile = {"domain": domain, "record_count": len(records), "fields": {}}

    for field, ftype in fields_config.items():
        values = [r.get(field) for r in records if r.get(field) is not None]

        if not values:
            continue

        if ftype == "numeric":
            nums = [float(v) for v in values if _is_numeric(v)]
            if not nums:
                continue
            profile["fields"][field] = {
                "type": "numeric",
                "count": len(nums),
                "mean": sum(nums) / len(nums),
                "std": _std(nums),
                "min": min(nums),
                "max": max(nums),
                "p25": _percentile(nums, 25),
                "p50": _percentile(nums, 50),
                "p75": _percentile(nums, 75),
            }

        elif ftype == "categorical":
            # Normalize booleans and mixed types to lowercase strings so that
            # Python True/False and JSON true/false map to the same key ("true"/"false")
            normalised = [
                str(v).lower() if not isinstance(v, str) else v.lower()
                for v in values
            ]
            counts = Counter(normalised)
            total = sum(counts.values())
            profile["fields"][field] = {
                "type": "categorical",
                "count": total,
                "distribution": {k: v / total for k, v in counts.items()},
            }

    return profile


def save_baseline(profile: dict, domain: str) -> Path:
    """Save baseline profile to disk."""
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    path = BASELINE_DIR / f"{domain}_baseline.json"
    with open(path, "w") as f:
        json.dump(profile, f, indent=2)
    return path


def load_baseline(domain: str) -> dict | None:
    """Load baseline profile from disk."""
    path = BASELINE_DIR / f"{domain}_baseline.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


# ── helpers ───────────────────────────────────────────────────────────────────

def _is_numeric(v) -> bool:
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


def _std(nums: list[float]) -> float:
    if len(nums) < 2:
        return 0.0
    mean = sum(nums) / len(nums)
    variance = sum((x - mean) ** 2 for x in nums) / (len(nums) - 1)
    return math.sqrt(variance)


def _percentile(nums: list[float], p: int) -> float:
    sorted_nums = sorted(nums)
    k = (len(sorted_nums) - 1) * p / 100
    f = int(k)
    c = f + 1
    if c >= len(sorted_nums):
        return sorted_nums[f]
    return sorted_nums[f] + (k - f) * (sorted_nums[c] - sorted_nums[f])

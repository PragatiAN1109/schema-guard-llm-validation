"""
SchemaGuard — Drift Package
"""

from drift.baseline import build_baseline, save_baseline, load_baseline
from drift.detector import detect_drift
from drift.drift_detector import generate_baseline, run_drift_detection, DOMAIN_FIELDS

__all__ = [
    "build_baseline", "save_baseline", "load_baseline",
    "detect_drift",
    "generate_baseline", "run_drift_detection", "DOMAIN_FIELDS",
]
from drift.analysis import build_realistic_baseline, create_shifted_dataset, run_full_drift_analysis

__all__ = [
    "build_baseline", "save_baseline", "load_baseline",
    "detect_drift",
    "generate_baseline", "run_drift_detection", "DOMAIN_FIELDS",
    "build_realistic_baseline", "create_shifted_dataset", "run_full_drift_analysis",
]

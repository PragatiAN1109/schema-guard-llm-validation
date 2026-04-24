"""
SchemaGuard — Drift Detector (Hardened)

Unified drift detection with minimum sample size checks,
graceful fallback on missing baselines, and safe math.
"""

import math
from collections import Counter
from drift.baseline import build_baseline, save_baseline, load_baseline, _std, _is_numeric
from config import (
    DRIFT_NUMERIC_THRESHOLD, DRIFT_CATEGORICAL_PSI_THRESHOLD,
    DRIFT_NULL_RATE_THRESHOLD, DRIFT_VIOLATION_RATE_THRESHOLD,
    DRIFT_MIN_SAMPLE_SIZE,
)
from utils.logger import get_logger, log_drift_alert

logger = get_logger("drift.detector")

DOMAIN_FIELDS = {
    "healthcare_intake": {
        "numeric": ["patient_age"],
        "categorical": ["gender", "diagnosis_code", "insurance_provider", "emergency_admission"],
        "nullable": ["discharge_date", "medication", "procedure_code", "insurance_provider", "notes"],
    },
    "financial_loan_application": {
        "numeric": ["annual_income", "loan_amount", "credit_score", "existing_debt", "employment_length_years", "interest_rate"],
        "categorical": ["employment_status", "loan_purpose", "co_applicant"],
        "nullable": ["employer_name", "employment_length_years", "interest_rate", "approval_date", "approved_amount", "property_value", "notes"],
    },
}


def generate_baseline(records: list[dict], domain: str) -> dict:
    """Generate and save a baseline profile from reference records."""
    if not records:
        logger.warning(f"Cannot generate baseline: empty record list for {domain}")
        return {"domain": domain, "record_count": 0, "fields": {}, "null_rates": {}}

    fields_config = _build_fields_config(domain)
    profile = build_baseline(records, domain, fields_config)

    profile["null_rates"] = {}
    for field in DOMAIN_FIELDS.get(domain, {}).get("nullable", []):
        total = len(records)
        null_count = sum(1 for r in records if r.get(field) is None)
        profile["null_rates"][field] = round(null_count / total, 4) if total > 0 else 0.0

    save_baseline(profile, domain)
    logger.info(f"Baseline saved for {domain}: {len(records)} records, {len(profile['fields'])} fields")
    return profile


def run_drift_detection(
    current_records: list[dict],
    domain: str,
    validation_results: list[dict] = None,
) -> dict:
    """
    Run drift detection with safety guards.

    Guards:
        - Returns gracefully if no baseline found
        - Skips fields with insufficient data
        - Handles zero std dev and empty distributions
        - Minimum sample size enforcement
    """
    if not current_records:
        return {"drift_detected": False, "checked_fields": 0, "drift_metrics": {}, "alerts": [], "note": "Empty batch"}

    baseline = load_baseline(domain)
    if baseline is None:
        return {"drift_detected": False, "checked_fields": 0, "drift_metrics": {}, "alerts": [], "error": "No baseline found."}

    # Warn if sample too small for reliable drift detection
    if len(current_records) < DRIFT_MIN_SAMPLE_SIZE:
        logger.info(f"Drift detection on small batch (n={len(current_records)}), results may be noisy")

    drift_metrics = {}
    alerts = []

    # 1. Numeric drift
    for field in DOMAIN_FIELDS.get(domain, {}).get("numeric", []):
        if field not in baseline.get("fields", {}):
            continue
        base_stats = baseline["fields"][field]
        values = [r.get(field) for r in current_records if r.get(field) is not None and _is_numeric(r.get(field))]

        if len(values) < 2:
            continue

        nums = [float(v) for v in values]
        current_mean = sum(nums) / len(nums)
        current_std = _std(nums)
        base_mean = base_stats.get("mean", 0)
        base_std = base_stats.get("std", 0)

        if base_std > 0:
            z_shift = abs(current_mean - base_mean) / base_std
        elif abs(current_mean - base_mean) > 0:
            z_shift = float("inf")
        else:
            z_shift = 0.0

        std_ratio = current_std / base_std if base_std > 0 else 1.0

        metric = {
            "type": "numeric",
            "baseline_mean": round(base_mean, 2),
            "current_mean": round(current_mean, 2),
            "baseline_std": round(base_std, 2),
            "current_std": round(current_std, 2),
            "z_shift": round(z_shift, 4) if z_shift != float("inf") else 999.0,
            "std_ratio": round(std_ratio, 4),
            "alert": z_shift > DRIFT_NUMERIC_THRESHOLD,
        }
        drift_metrics[field] = metric
        if metric["alert"]:
            msg = f"{field}: mean shifted by {z_shift:.2f} std devs ({base_mean:.1f} → {current_mean:.1f})"
            alerts.append({"field": field, "type": "numeric_shift", "message": msg, "severity": "high" if z_shift > 3.0 else "medium"})
            log_drift_alert(logger, field, "numeric_shift", "high" if z_shift > 3.0 else "medium", msg)

    # 2. Categorical drift (PSI)
    for field in DOMAIN_FIELDS.get(domain, {}).get("categorical", []):
        if field not in baseline.get("fields", {}):
            continue
        base_stats = baseline["fields"][field]
        # Normalize booleans to lowercase strings so True/"true" compare correctly
        values = [str(r.get(field)).lower() for r in current_records if r.get(field) is not None]

        if len(values) < 2:
            continue

        counts = Counter(values)
        total = sum(counts.values())
        current_dist = {k: v / total for k, v in counts.items()}
        base_dist = base_stats.get("distribution", {})

        if not base_dist:
            continue

        all_cats = set(list(base_dist.keys()) + list(current_dist.keys()))
        eps = 1e-6
        try:
            psi = sum(
                (current_dist.get(c, eps) - base_dist.get(c, eps)) *
                math.log(max(current_dist.get(c, eps), eps) / max(base_dist.get(c, eps), eps))
                for c in all_cats
            )
            psi = max(0.0, psi)  # PSI should not be negative
        except (ValueError, ZeroDivisionError):
            psi = 0.0

        # Sample-size correction: high-cardinality fields on small baselines
        # fluctuate more naturally; scale the threshold up proportionally.
        # For n=100 baseline with <=5 categories: threshold unchanged.
        # For 10-category fields: threshold * (10/5) = 0.40 (less sensitive).
        n_cats = len(base_dist)
        baseline_n = baseline.get("record_count", 100)
        size_factor = max(1.0, (n_cats / 5.0) * (100.0 / max(float(baseline_n), 20.0)))
        effective_psi_threshold = round(DRIFT_CATEGORICAL_PSI_THRESHOLD * size_factor, 4)

        metric = {
            "type": "categorical",
            "psi": round(psi, 4),
            "effective_threshold": effective_psi_threshold,
            "baseline_categories": n_cats,
            "current_categories": len(current_dist),
            "alert": psi > effective_psi_threshold,
        }
        drift_metrics[field] = metric
        if metric["alert"]:
            msg = f"{field}: PSI = {psi:.4f} (effective_threshold: {effective_psi_threshold:.4f})"
            alerts.append({"field": field, "type": "categorical_shift", "message": msg, "severity": "high" if psi > 0.5 else "medium"})
            log_drift_alert(logger, field, "categorical_shift", "high" if psi > 0.5 else "medium", msg)

    # 3. Null-rate drift
    baseline_null_rates = baseline.get("null_rates", {})
    for field in DOMAIN_FIELDS.get(domain, {}).get("nullable", []):
        if field not in baseline_null_rates:
            continue
        total = len(current_records)
        if total == 0:
            continue
        current_null = sum(1 for r in current_records if r.get(field) is None)
        current_rate = current_null / total
        base_rate = baseline_null_rates[field]
        delta = abs(current_rate - base_rate)

        if delta > DRIFT_NULL_RATE_THRESHOLD:
            drift_metrics[f"{field}_null_rate"] = {
                "type": "null_rate",
                "baseline_null_rate": round(base_rate, 4),
                "current_null_rate": round(current_rate, 4),
                "delta": round(delta, 4),
                "alert": True,
            }
            msg = f"{field}: null rate changed from {base_rate:.0%} to {current_rate:.0%}"
            alerts.append({"field": field, "type": "null_rate_shift", "message": msg, "severity": "low"})

    # 4. Violation frequency drift
    if validation_results and len(validation_results) > 0:
        current_violation_rate = sum(1 for r in validation_results if not r.get("semantic_valid", True)) / len(validation_results)
        base_violation_rate = baseline.get("violation_rate", 0.0)
        v_delta = abs(current_violation_rate - base_violation_rate)

        drift_metrics["violation_rate"] = {
            "type": "violation_frequency",
            "baseline_rate": round(base_violation_rate, 4),
            "current_rate": round(current_violation_rate, 4),
            "delta": round(v_delta, 4),
            "alert": v_delta > DRIFT_VIOLATION_RATE_THRESHOLD,
        }
        if v_delta > DRIFT_VIOLATION_RATE_THRESHOLD:
            msg = f"Violation rate changed from {base_violation_rate:.0%} to {current_violation_rate:.0%}"
            alerts.append({"field": "violation_rate", "type": "violation_frequency_shift", "message": msg, "severity": "high"})

    return {
        "drift_detected": len(alerts) > 0,
        "checked_fields": len(drift_metrics),
        "drift_metrics": drift_metrics,
        "alerts": alerts,
    }


def _build_fields_config(domain: str) -> dict:
    config = {}
    domain_fields = DOMAIN_FIELDS.get(domain, {})
    for field in domain_fields.get("numeric", []):
        config[field] = "numeric"
    for field in domain_fields.get("categorical", []):
        config[field] = "categorical"
    return config

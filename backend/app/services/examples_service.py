"""
Examples Service — returns curated sample records for each domain.
"""

import json
from pathlib import Path

SEED_DIR = Path(__file__).parent.parent.parent.parent / "data_gen" / "sample_data"
SEED_FILES = {
    "healthcare_intake": "healthcare_seed_examples.json",
    "financial_loan_application": "finance_seed_examples.json",
}

_cache: dict = {}


def _load_seeds(domain: str) -> list[dict]:
    if domain in _cache:
        return _cache[domain]
    path = SEED_DIR / SEED_FILES.get(domain, "")
    if not path.exists():
        return []
    with open(path) as f:
        seeds = json.load(f)
    _cache[domain] = seeds
    return seeds


def get_examples() -> dict:
    """Return curated examples for all domains, organized for the frontend."""
    output = {}
    for domain, filename in SEED_FILES.items():
        seeds = _load_seeds(domain)
        label = "healthcare" if "healthcare" in domain else "finance"
        output[label] = {
            "domain": domain,
            "examples": [
                {
                    "record_id": s["record_id"],
                    "category": s["category"],
                    "notes": s.get("notes", ""),
                    "record": s["record"],
                }
                for s in seeds
            ],
        }
    return output


def get_example_by_category(domain: str, category: str = "valid") -> list[dict]:
    """Return examples filtered by category."""
    seeds = _load_seeds(domain)
    return [
        {"record_id": s["record_id"], "category": s["category"], "notes": s.get("notes",""), "record": s["record"]}
        for s in seeds if s["category"] == category
    ]

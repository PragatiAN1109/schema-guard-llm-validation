"""
Seed the SQLite database with demo validation history.

Run once to make the dashboard look alive:
    cd schema-guard-llm-validation
    python backend/seed_demo_data.py
"""

import sys
import json
import logging
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
logging.disable(logging.WARNING)

from backend.app.db.database import init_db, save_validation_run, save_batch_run
from validator.pipeline import validate_record
from validator.batch_validation import validate_batch
from drift.drift_detector import generate_baseline

SEED_DIR = ROOT / "data_gen" / "sample_data"


def load_seeds(filename):
    with open(SEED_DIR / filename) as f:
        return json.load(f)


def main():
    print("Initializing database...")
    init_db()

    hc_seeds = load_seeds("healthcare_seed_examples.json")
    fn_seeds = load_seeds("finance_seed_examples.json")

    # Single-record validations
    print("Seeding single-record validations...")
    count = 0
    for seeds, domain in [(hc_seeds, "healthcare_intake"), (fn_seeds, "financial_loan_application")]:
        for s in seeds:
            result = validate_record(s["record"], domain, record_id=s["record_id"])
            result["input_payload"] = s["record"]
            save_validation_run(result)
            count += 1
    print(f"  {count} validation runs saved")

    # Batch validations
    print("Seeding batch runs...")
    for seeds, domain in [(hc_seeds, "healthcare_intake"), (fn_seeds, "financial_loan_application")]:
        valid_recs = [s["record"] for s in seeds if s["category"] == "valid"]
        if valid_recs:
            generate_baseline(valid_recs, domain)
        all_recs = [s["record"] for s in seeds]
        result = validate_batch(all_recs, domain, run_drift=True)
        save_batch_run(result)
    print("  2 batch runs saved")

    print("Done. Database ready for demo.")


if __name__ == "__main__":
    main()

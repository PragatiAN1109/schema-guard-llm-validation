"""
SchemaGuard — Quick Demo (< 30 seconds)

Perfect for live demos. Shows input → validation → score → decision.

Usage:
    cd schema-guard-llm-validation
    python demo/quick_demo.py
"""

import sys
import json
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
logging.disable(logging.WARNING)

from validator.pipeline import validate_record

G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"; B = "\033[1m"; D = "\033[2m"; C = "\033[96m"; RST = "\033[0m"


def decision_badge(d):
    if d == "trusted": return f"{G}█ TRUSTED{RST}"
    if d == "flagged": return f"{Y}█ FLAGGED{RST}"
    return f"{R}█ QUARANTINED{RST}"


def show(label, record, domain, record_id):
    print(f"\n{C}{'─' * 56}{RST}")
    print(f"  {B}{label}{RST}")
    print(f"{C}{'─' * 56}{RST}")

    r = validate_record(record, domain, record_id=record_id)

    print(f"  Structural:  {'✅' if r['structural_valid'] else '❌'}")
    print(f"  Semantic:    {'✅' if r['semantic_valid'] else '❌'}")
    print(f"  Confidence:  {r['confidence_score']:.2f}")
    print(f"  Decision:    {decision_badge(r['decision'])}")

    for v in r.get("violated_rules", []):
        sev = "🔴" if v["severity"] == "critical" else "🟡"
        print(f"  {sev} {v['rule_id']}: {v['message']}")


def main():
    print(f"\n{B}{'═' * 56}{RST}")
    print(f"{B}  🛡️  SchemaGuard — Quick Demo{RST}")
    print(f"{B}{'═' * 56}{RST}")

    # 1: Valid
    show("Valid Patient Record", {
        "patient_id": "P-3021", "first_name": "James", "last_name": "Carter",
        "date_of_birth": "1978-11-02", "gender": "male",
        "admission_date": "2024-09-14", "discharge_date": "2024-09-19",
        "diagnosis_code": "J18.9", "diagnosis_description": "Pneumonia",
        "treating_physician": "Dr. Park", "medication": "Azithromycin",
        "procedure_code": None, "insurance_provider": "Aetna",
        "patient_age": 45, "emergency_admission": False, "notes": None,
    }, "healthcare", "DEMO-001")

    # 2: Temporal contradiction
    show("Discharge Before Admission", {
        "patient_id": "P-4412", "first_name": "Sarah", "last_name": "Mitchell",
        "date_of_birth": "1990-01-20", "gender": "female",
        "admission_date": "2024-08-15", "discharge_date": "2024-08-08",
        "diagnosis_code": "N39.0", "diagnosis_description": "UTI",
        "treating_physician": "Dr. Evans", "medication": "Ciprofloxacin",
        "procedure_code": None, "insurance_provider": "UnitedHealth",
        "patient_age": 34, "emergency_admission": False, "notes": None,
    }, "healthcare", "DEMO-002")

    # 3: Ratio violation
    show("Loan 52x Income", {
        "application_id": "LA-33190", "applicant_name": "Jessica Williams",
        "date_of_birth": "1991-06-18", "annual_income": 48000,
        "employment_status": "employed", "employer_name": "Target",
        "employment_length_years": 3, "loan_amount": 2500000,
        "loan_purpose": "home_purchase", "loan_term_months": 360,
        "interest_rate": 6.5, "credit_score": 680, "existing_debt": 15000,
        "application_date": "2024-05-12", "approval_date": None,
        "approved_amount": None, "property_value": 2600000,
        "co_applicant": False, "notes": None,
    }, "finance", "DEMO-003")

    print(f"\n{B}{'═' * 56}{RST}")
    print(f"  {G}3 records validated in < 1 second{RST}")
    print(f"{B}{'═' * 56}{RST}\n")


if __name__ == "__main__":
    main()

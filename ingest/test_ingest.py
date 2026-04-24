#!/usr/bin/env python3
"""
SchemaGuard — Document Ingest CLI Test
========================================
Smoke-tests the full ingest pipeline without needing the FastAPI server.

Usage:
    # Test with a sample text document (no file needed — uses inline fixture)
    python3 ingest/test_ingest.py

    # Test with a real file
    python3 ingest/test_ingest.py --file /path/to/doc.pdf --domain healthcare
    python3 ingest/test_ingest.py --file /path/to/loan.txt --domain finance
"""

import sys, json, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── sample fixtures (used when no file is provided) ────────────────────────

_HC_SAMPLE = """\
Patient Intake Summary
======================
Name: Sarah Mitchell        DOB: January 20, 1990
Patient ID: P-4412          Gender: Female
Insurance: UnitedHealth     Emergency admission: No

Admission date:  August 15, 2024
Discharge date:  August 22, 2024

Diagnosis: Urinary tract infection (N39.0)
Treating physician: Dr. Mark Evans
Medication prescribed: Ciprofloxacin 500mg twice daily
Age: 34
Notes: Recurrent UTI, responded well to antibiotics.
"""

_FN_SAMPLE = """\
LOAN APPLICATION — PERSONAL / HOME PURCHASE
============================================
Applicant: Michael Torres         DOB: May 22, 1988
Application ID: LA-40821          Date: August 10, 2024

Employment: Employed at Deloitte for 6 years
Annual income: $92,000
Credit score: 742
Existing debt: $18,000

Loan requested: $320,000
Purpose: home_purchase
Term: 360 months
Interest rate: 6.75%
Property value: $415,000
Co-applicant: No

Approval date: August 24, 2024
Approved amount: $310,000
"""

_FIXTURES = {
    "healthcare_intake":          ("sample_patient.txt", _HC_SAMPLE.encode()),
    "financial_loan_application": ("sample_loan.txt",    _FN_SAMPLE.encode()),
}


def run_test(file_bytes: bytes, filename: str, domain: str) -> None:
    from ingest.document_ingest import extract_and_validate

    print(f"\n{'='*60}")
    print(f"  SchemaGuard Document Ingest Test")
    print(f"{'='*60}")
    print(f"  File  : {filename}")
    print(f"  Domain: {domain}")
    print(f"  Size  : {len(file_bytes):,} bytes")

    result = extract_and_validate(file_bytes, filename, domain)

    # ── extracted record ──────────────────────────────────────────────────
    print(f"\n[1/3] Text extraction OK  ({len(result.extracted_text)} chars preview)")
    print(f"\n[2/3] Extracted JSON record:")
    print(json.dumps(result.extracted_record, indent=2, default=str))

    # ── validation result ─────────────────────────────────────────────────
    val = result.validation
    print(f"\n[3/3] Validation result:")
    print(f"  decision         : {val.get('decision')}")
    print(f"  confidence_score : {val.get('confidence_score')}")
    print(f"  structural_valid : {val.get('structural_valid')}")
    print(f"  semantic_valid   : {val.get('semantic_valid')}")

    violations = val.get("violated_rules", [])
    if violations:
        print(f"  violated_rules   :")
        for v in violations:
            print(f"    [{v.get('rule_id')}] {v.get('message', '')}")
    else:
        print(f"  violated_rules   : []  (no violations)")

    print(f"\n  explanation: {val.get('explanation', '')[:200]}")
    print(f"\n  ingest_latency_ms: {result.latency_ms}")
    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="SchemaGuard Document Ingest Test")
    parser.add_argument("--file",   type=str, default=None,
                        help="Path to PDF or text file to ingest")
    parser.add_argument("--domain", type=str, default="healthcare_intake",
                        help="Domain: healthcare_intake or financial_loan_application")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"ERROR: file not found: {path}")
            sys.exit(1)
        file_bytes = path.read_bytes()
        filename   = path.name
        domain     = args.domain
    else:
        # Use built-in fixture
        domain = args.domain
        if domain not in _FIXTURES and domain in ("healthcare", "finance"):
            domain = {"healthcare": "healthcare_intake",
                      "finance":   "financial_loan_application"}[domain]
        if domain not in _FIXTURES:
            domain = "healthcare_intake"
        filename, file_bytes = _FIXTURES[domain]
        print(f"\n(No --file supplied — using built-in {domain} fixture)")

    run_test(file_bytes, filename, domain)


if __name__ == "__main__":
    main()

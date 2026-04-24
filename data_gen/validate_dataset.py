"""
SchemaGuard — Dataset Validator
================================
Audits generated datasets for correctness after generation.

Usage:
    python data_gen/validate_dataset.py                     # both
    python data_gen/validate_dataset.py --domain hc
    python data_gen/validate_dataset.py --domain fn
    python data_gen/validate_dataset.py --report            # save CSV report
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import jsonschema
except ImportError:
    print("pip install jsonschema")
    sys.exit(1)

DATA_DIR   = PROJECT_ROOT / "data"
SCHEMA_DIR = PROJECT_ROOT / "schemas"

DOMAIN_FILES = {
    "healthcare_intake":          "healthcare_dataset.json",
    "financial_loan_application": "finance_dataset.json",
}


# ── helpers (same inline logic as generator) ──────────────────────────────────
def _parse_date(s):
    if not s: return None
    try: return datetime.strptime(s, "%Y-%m-%d").date()
    except: return None

def _age(dob, ref):
    y = ref.year - dob.year
    if (ref.month, ref.day) < (dob.month, dob.day): y -= 1
    return y

ADULT_ONLY = {"M81.0","M81.8","I25.10","I25.11","E11.9","E11.65","N40.0","C61"}
MED_MAP = {
    "E11": {"Metformin","Insulin","Glipizide","Sitagliptin","Empagliflozin","Pioglitazone"},
    "J18": {"Azithromycin","Amoxicillin","Levofloxacin","Ceftriaxone","Doxycycline"},
    "J06": {"Amoxicillin","Ibuprofen","Acetaminophen"},
    "I10": {"Lisinopril","Amlodipine","Losartan","Hydrochlorothiazide","Metoprolol"},
    "I25": {"Atorvastatin","Aspirin","Clopidogrel","Metoprolol","Lisinopril"},
    "N39": {"Ciprofloxacin","Nitrofurantoin","Trimethoprim","Amoxicillin"},
    "K21": {"Omeprazole","Pantoprazole","Esomeprazole","Ranitidine","Famotidine"},
}

def semantic_hc(record):
    v = []
    dob  = _parse_date(record.get("date_of_birth"))
    adm  = _parse_date(record.get("admission_date"))
    disc = _parse_date(record.get("discharge_date"))
    age  = record.get("patient_age")
    code = record.get("diagnosis_code","")
    med  = record.get("medication")
    if dob and adm and age is not None:
        if abs(_age(dob, adm) - age) > 1: v.append("HC-001")
    if dob and adm:
        if adm < dob: v.append("HC-002")
    if adm and disc:
        if disc < adm: v.append("HC-003")
    if age is not None and code in ADULT_ONLY and age < 18:
        v.append("HC-004")
    if med and code:
        cat = code[:3]
        known = MED_MAP.get(cat)
        if known and med not in known: v.append("HC-005")
    return v

def semantic_fn(record):
    v = []
    app  = _parse_date(record.get("application_date"))
    appr = _parse_date(record.get("approval_date"))
    dob  = _parse_date(record.get("date_of_birth"))
    income = record.get("annual_income", 0) or 0
    loan   = record.get("loan_amount",   0) or 0
    debt   = record.get("existing_debt", 0) or 0
    emp    = record.get("employment_length_years")
    appr_a = record.get("approved_amount")
    if app and appr and appr < app:             v.append("FN-001")
    if income > 0 and loan / income > 10:       v.append("FN-002")
    if income > 0 and (debt+loan)/income > 0.6: v.append("FN-003")
    if dob and app and emp is not None:
        if emp > _age(dob, app) - 18:           v.append("FN-004")
    if appr_a is not None and loan > 0 and appr_a > loan: v.append("FN-005")
    return v

_schema_cache = {}
def load_schema(domain):
    if domain not in _schema_cache:
        fname = "healthcare_schema.json" if "healthcare" in domain else "finance_schema.json"
        with open(SCHEMA_DIR / fname) as f:
            _schema_cache[domain] = json.load(f)
    return _schema_cache[domain]

def struct_ok(record, domain):
    schema = load_schema(domain)
    v = jsonschema.Draft7Validator(schema)
    errs = list(v.iter_errors(record))
    return len(errs) == 0, [e.message for e in errs]


# ── audit one dataset ──────────────────────────────────────────────────────────
def audit_dataset(domain: str) -> dict:
    fname = DOMAIN_FILES[domain]
    path  = DATA_DIR / fname
    if not path.exists():
        print(f"  [skip] {path} not found — run generation first")
        return {}

    with open(path) as f:
        records = json.load(f)

    issues = []
    stats  = defaultdict(int)
    rule_dist = defaultdict(int)

    for r in records:
        rid  = r.get("record_id","?")
        cat  = r.get("category","?")
        rec  = r.get("record",{})
        labs = r.get("labels",{})
        labeled_rules = set(labs.get("violated_rules",[]))

        stats["total"] += 1
        stats[cat] += 1

        # 1. Structural check
        ok, errs = struct_ok(rec, domain)
        if not ok:
            issues.append({"record_id": rid, "type": "structural_invalid", "detail": errs[:2]})
            stats["structural_invalid"] += 1

        # 2. Semantic check — does the actual violation match the label?
        checker = semantic_hc if "healthcare" in domain else semantic_fn
        actual_rules = set(checker(rec))

        for rule in actual_rules:
            rule_dist[rule] += 1

        if cat == "invalid":
            if not actual_rules:
                issues.append({"record_id": rid, "type": "missing_violation",
                                "detail": f"labeled {labeled_rules}, detected none"})
                stats["label_mismatch"] += 1
            elif actual_rules != labeled_rules:
                # allow superset (borderline records can trigger extra rules)
                if not labeled_rules.issubset(actual_rules):
                    issues.append({"record_id": rid, "type": "wrong_violation",
                                    "detail": f"labeled {labeled_rules}, detected {actual_rules}"})
                    stats["label_mismatch"] += 1
        elif cat in ("valid", "edge_case"):
            if actual_rules:
                issues.append({"record_id": rid, "type": "unexpected_violation",
                                "detail": f"category={cat} but triggered {actual_rules}"})
                stats["unexpected_violation"] += 1

    stats["issues"]    = len(issues)
    stats["clean"]     = stats["total"] - stats["issues"]
    stats["rule_dist"] = dict(rule_dist)
    return {"domain": domain, "stats": dict(stats), "issues": issues[:20]}  # cap issue list


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", choices=["hc","fn","both"], default="both")
    parser.add_argument("--report", action="store_true", help="Save CSV audit report")
    args = parser.parse_args()

    domains = []
    if args.domain in ("hc","both"):  domains.append("healthcare_intake")
    if args.domain in ("fn","both"):  domains.append("financial_loan_application")

    all_results = []
    for domain in domains:
        label = "Healthcare" if "health" in domain else "Finance"
        print(f"\n{'═'*60}")
        print(f"  Auditing: {label}")
        print(f"{'═'*60}")
        result = audit_dataset(domain)
        if not result:
            continue
        all_results.append(result)

        s = result["stats"]
        print(f"\n  Total records   : {s.get('total',0)}")
        print(f"  Valid           : {s.get('valid',0)}")
        print(f"  Invalid         : {s.get('invalid',0)}")
        print(f"  Edge case       : {s.get('edge_case',0)}")
        print(f"  ─────────────────────────────")
        print(f"  Structural bad  : {s.get('structural_invalid',0)}")
        print(f"  Label mismatches: {s.get('label_mismatch',0)}")
        print(f"  Unexpected viol : {s.get('unexpected_violation',0)}")
        print(f"  ─────────────────────────────")
        total_issues = s.get("issues", 0)
        clean        = s.get("clean",  0)
        pct = 100 * clean / s.get("total",1)
        print(f"  Issues total    : {total_issues}")
        print(f"  Clean records   : {clean}  ({pct:.1f}%)")

        rd = s.get("rule_dist", {})
        if rd:
            print(f"\n  Rule distribution (detected violations):")
            for rule, cnt in sorted(rd.items()):
                bar = "█" * cnt
                print(f"    {rule}  {cnt:>4}  {bar}")

        if result["issues"]:
            print(f"\n  Sample issues (first {min(5,len(result['issues']))}):")
            for issue in result["issues"][:5]:
                print(f"    [{issue['record_id']}] {issue['type']}: {issue['detail']}")

    if args.report and all_results:
        import csv
        report_path = DATA_DIR / "audit_report.csv"
        rows = []
        for result in all_results:
            s = result["stats"]
            rows.append({
                "domain":              result["domain"],
                "total":               s.get("total",0),
                "valid":               s.get("valid",0),
                "invalid":             s.get("invalid",0),
                "edge_case":           s.get("edge_case",0),
                "structural_invalid":  s.get("structural_invalid",0),
                "label_mismatch":      s.get("label_mismatch",0),
                "unexpected_violation":s.get("unexpected_violation",0),
                "clean":               s.get("clean",0),
            })
        with open(report_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader(); writer.writerows(rows)
        print(f"\n  Audit report saved: {report_path}")

    print()

if __name__ == "__main__":
    main()

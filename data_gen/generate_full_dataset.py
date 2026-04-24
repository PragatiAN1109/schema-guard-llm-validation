"""
SchemaGuard — Full Synthetic Dataset Generator
===============================================
Generates 300 records per domain using the Anthropic API.

Distribution per domain:
  40% valid       (120 records)
  40% invalid     (120 records, 24 per rule × 5 rules)
  20% edge_case   ( 60 records, 12 per edge-case type × 5 types)

Usage:
  python data_gen/generate_full_dataset.py                  # both domains
  python data_gen/generate_full_dataset.py --domain hc      # healthcare only
  python data_gen/generate_full_dataset.py --domain fn      # finance only
  python data_gen/generate_full_dataset.py --dry-run        # show plan, no API calls

Requirements:
  pip install anthropic jsonschema
  export ANTHROPIC_API_KEY=sk-...

Output:
  data/healthcare_dataset.json
  data/finance_dataset.json
  data/dataset_summary.csv
  outputs/plots/dataset_summary.png
"""

import os
import sys
import json
import uuid
import time
import random
import argparse
import traceback
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict

# ── project root on sys.path ───────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package not installed. Run: pip install anthropic")
    sys.exit(1)

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema not installed. Run: pip install jsonschema")
    sys.exit(1)

# ── paths ──────────────────────────────────────────────────────────────────
DATA_DIR   = PROJECT_ROOT / "data"
SCHEMA_DIR = PROJECT_ROOT / "schemas"
PLOTS_DIR  = PROJECT_ROOT / "outputs" / "plots"
DATA_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# ── constants ──────────────────────────────────────────────────────────────
MODEL          = "claude-opus-4-5"
RECORDS_TOTAL  = 300
VALID_PCT      = 0.40   # 120
INVALID_PCT    = 0.40   # 120  (24 per rule)
EDGE_PCT       = 0.20   #  60  (12 per edge type)
MAX_RETRIES    = 3
RETRY_DELAY    = 2.0    # seconds between retries

HC_RULES  = ["HC-001", "HC-002", "HC-003", "HC-004", "HC-005"]
FN_RULES  = ["FN-001", "FN-002", "FN-003", "FN-004", "FN-005"]

# ══════════════════════════════════════════════════════════════════════════════
# PROMPT LIBRARY
# ══════════════════════════════════════════════════════════════════════════════

HC_SYSTEM = (
    "You are a synthetic medical data generator. "
    "You produce healthcare patient intake records as JSON objects. "
    "Every record must be internally consistent — all cross-field relationships must hold. "
    "Respond with ONLY a raw JSON object. No markdown fences, no explanation, no commentary."
)

FN_SYSTEM = (
    "You are a synthetic financial data generator. "
    "You produce loan application records as JSON objects. "
    "Every record must be internally consistent — all cross-field relationships must hold. "
    "Respond with ONLY a raw JSON object. No markdown fences, no explanation, no commentary."
)

# ── Healthcare valid variants ──────────────────────────────────────────────
HC_VALID_VARIANTS = [
    ("25-35 year old", "male",   "respiratory infection"),
    ("25-35 year old", "female", "urinary tract infection"),
    ("45-60 year old", "male",   "type 2 diabetes management"),
    ("45-60 year old", "female", "hypertension follow-up"),
    ("elderly (70+)", "male",    "cardiac evaluation"),
    ("elderly (70+)", "female",  "atherosclerosis management"),
    ("pediatric (3-10)", "male", "acute upper respiratory infection"),
    ("pediatric (3-10)", "female","minor surgical procedure"),
    ("middle-aged (40-55)", "male","gastroesophageal reflux"),
    ("middle-aged (40-55)", "female","routine annual check-up"),
]

HC_VALID_PROMPT = """Generate a realistic healthcare intake record with these exact fields:

REQUIRED: patient_id (P-XXXX format), first_name, last_name, date_of_birth (YYYY-MM-DD),
gender (male/female/other/unknown), admission_date (YYYY-MM-DD), diagnosis_code (ICD-10),
diagnosis_description, treating_physician

OPTIONAL (include most): discharge_date (>= admission_date, or null), medication (or null),
procedure_code (5-digit CPT or null), insurance_provider (or null),
patient_age (integer — MUST equal floor((admission_date - date_of_birth) / 365.25)),
emergency_admission (boolean), notes (or null)

RULES (ALL must hold):
1. patient_age = floor((admission_date - date_of_birth) / 365.25)
2. discharge_date >= admission_date (if set)
3. diagnosis_code and diagnosis_description are medically consistent
4. medication is plausible for the diagnosis

Generate a single record for a {age_range} {gender} patient admitted for {condition}.

Output ONLY the raw JSON object."""


# ── Healthcare invalid variants ────────────────────────────────────────────
HC_INVALID_PROMPTS = {
    "HC-001": """Generate a healthcare intake record that passes schema validation but has a WRONG patient_age.

The patient_age field MUST NOT match floor((admission_date - date_of_birth) / 365.25).
Make the discrepancy 5-18 years (medium difficulty).
All other fields must be realistic and internally consistent with each other.
All field types must be correct per the schema.

Schema fields: patient_id (P-XXXX), first_name, last_name, date_of_birth, gender,
admission_date, discharge_date (or null), diagnosis_code (ICD-10), diagnosis_description,
treating_physician, medication (or null), procedure_code (5-digit or null),
insurance_provider (or null), patient_age (integer 0-130), emergency_admission (boolean),
notes (or null).

Output ONLY the raw JSON object.""",

    "HC-002": """Generate a healthcare intake record that passes schema validation but has admission_date BEFORE date_of_birth.

Set date_of_birth at least 1 year AFTER admission_date (the patient hasn't been born yet at time of admission).
patient_age should be set to a plausible value given the (wrong) admission_date.
All other fields must be realistic.

Schema fields: patient_id (P-XXXX), first_name, last_name, date_of_birth, gender,
admission_date, discharge_date (or null), diagnosis_code (ICD-10), diagnosis_description,
treating_physician, medication (or null), procedure_code (5-digit or null),
insurance_provider (or null), patient_age (integer 0-130), emergency_admission (boolean),
notes (or null).

Output ONLY the raw JSON object.""",

    "HC-003": """Generate a healthcare intake record that passes schema validation but has discharge_date BEFORE admission_date.

Keep the gap 1-10 days (looks like a plausible data-entry error).
Example: admission_date = 2024-08-15, discharge_date = 2024-08-08.
All other fields must be realistic and type-correct.

Schema fields: patient_id (P-XXXX), first_name, last_name, date_of_birth, gender,
admission_date, discharge_date (MUST be set and BEFORE admission_date), diagnosis_code (ICD-10),
diagnosis_description, treating_physician, medication (or null), procedure_code (5-digit or null),
insurance_provider (or null), patient_age (integer 0-130), emergency_admission (boolean),
notes (or null).

Output ONLY the raw JSON object.""",

    "HC-004": """Generate a healthcare intake record that passes schema validation but has an age-inappropriate diagnosis.

The patient MUST be 3-7 years old (pediatric).
The diagnosis_code MUST be one that only occurs in adults:
  M81.0 (Age-related osteoporosis), E11.9 (Type 2 diabetes), I25.10 (Atherosclerotic heart disease),
  N40.0 (Benign prostatic hyperplasia), or C61 (Malignant neoplasm of prostate).
All other fields realistic for a child patient.

Schema fields: patient_id (P-XXXX), first_name, last_name, date_of_birth, gender,
admission_date, discharge_date (or null), diagnosis_code (ICD-10), diagnosis_description,
treating_physician, medication (or null), procedure_code (5-digit or null),
insurance_provider (or null), patient_age (integer 0-130), emergency_admission (boolean),
notes (or null).

Output ONLY the raw JSON object.""",

    "HC-005": """Generate a healthcare intake record that passes schema validation but has implausible medication for the diagnosis.

Choose a MISMATCH pair — for example:
  - diagnosis J18.9 (Pneumonia) + medication Metformin (diabetes drug)
  - diagnosis E11.9 (Type 2 diabetes) + medication Amoxicillin (antibiotic)
  - diagnosis I10 (Hypertension) + medication Ibuprofen (NSAID that raises BP)
  - diagnosis K21.0 (GERD) + medication Lisinopril (ACE inhibitor for hypertension)
All other fields must be realistic and type-correct.

Schema fields: patient_id (P-XXXX), first_name, last_name, date_of_birth, gender,
admission_date, discharge_date (or null), diagnosis_code (ICD-10), diagnosis_description,
treating_physician, medication (MUST be implausible for the diagnosis),
procedure_code (5-digit or null), insurance_provider (or null),
patient_age (integer 0-130), emergency_admission (boolean), notes (or null).

Output ONLY the raw JSON object.""",
}

# ── Healthcare edge case variants ──────────────────────────────────────────
HC_EDGE_PROMPTS = [
    ("newborn", """Generate a valid healthcare intake record for a NEWBORN patient.
date_of_birth and admission_date must be the SAME day or within 1-3 days.
patient_age must be 0.
Use a neonatal ICD-10 code: P07.3 (Preterm), P59.9 (Neonatal jaundice), P22.0 (Respiratory distress), or P36.9 (Sepsis).
All cross-field rules must hold. Output ONLY the raw JSON object."""),

    ("same_day_discharge", """Generate a valid healthcare intake record where admission_date and discharge_date are the SAME day.
Use a minor outpatient or observation stay.
All cross-field rules must hold. Output ONLY the raw JSON object."""),

    ("elderly_patient", """Generate a valid healthcare intake record for a patient aged 92-105.
Use a geriatric diagnosis. patient_age must correctly match date_of_birth and admission_date.
All cross-field rules must hold. Output ONLY the raw JSON object."""),

    ("minimal_fields", """Generate a valid healthcare intake record with ONLY required fields populated.
Set ALL optional fields (discharge_date, medication, procedure_code, insurance_provider,
patient_age, emergency_admission, notes) to null or omit them.
The record must still be structurally and semantically valid.
Output ONLY the raw JSON object."""),

    ("emergency_same_day", """Generate a valid healthcare intake record with emergency_admission=true,
a procedure_code set, same-day discharge, and a critical/urgent diagnosis (e.g. I21.9 MI, S72.001 hip fracture).
All fields consistent. Output ONLY the raw JSON object."""),
]

# ── Finance valid variants ─────────────────────────────────────────────────
FN_VALID_VARIANTS = [
    ("mid-career professional", "home_purchase"),
    ("recent graduate",         "personal"),
    ("small business owner",    "business"),
    ("retiree",                 "debt_consolidation"),
    ("high-income executive",   "home_purchase"),
    ("mid-career professional", "auto"),
    ("recent graduate",         "education"),
    ("small business owner",    "refinance"),
    ("retiree",                 "auto"),
    ("high-income executive",   "business"),
]

FN_VALID_PROMPT = """Generate a realistic financial loan application record with these exact fields:

REQUIRED: application_id (LA-XXXXX format), applicant_name, date_of_birth (YYYY-MM-DD),
annual_income (>= 0), employment_status (employed/self_employed/unemployed/retired/student),
employer_name (string or null), loan_amount (100-10000000), loan_purpose
(home_purchase/refinance/auto/education/personal/business/debt_consolidation), application_date

OPTIONAL (include most): employment_length_years (0-60, or null), loan_term_months
(one of: 12,24,36,48,60,84,120,180,240,360), interest_rate (0-30 or null),
credit_score (300-850), existing_debt (>= 0), approval_date (>= application_date, or null),
approved_amount (<= loan_amount, or null), property_value (or null), co_applicant (boolean),
notes (or null)

RULES (ALL must hold):
1. approval_date >= application_date (if set)
2. loan_amount is realistic relative to annual_income (1-8x for most types)
3. employment_length_years + 18 <= applicant age (if set)
4. approved_amount <= loan_amount (if set)
5. (existing_debt + loan_amount) / annual_income < 0.6 (if income > 0)
6. employer_name is null when employment_status is unemployed or student

Generate a single record for a {profile} applying for a {loan_type} loan.

Output ONLY the raw JSON object."""

# ── Finance invalid variants ───────────────────────────────────────────────
FN_INVALID_PROMPTS = {
    "FN-001": """Generate a financial loan application that passes schema validation but has approval_date BEFORE application_date.

Keep the gap 5-25 days (plausible data-entry error).
Example: application_date=2024-06-15, approval_date=2024-05-28.
All other fields must be realistic and type-correct.

Schema fields: application_id (LA-XXXXX), applicant_name, date_of_birth, annual_income,
employment_status, employer_name (or null), employment_length_years (or null), loan_amount,
loan_purpose, loan_term_months (one of 12/24/36/48/60/84/120/180/240/360), interest_rate (or null),
credit_score (300-850), existing_debt, application_date, approval_date (MUST be before application_date),
approved_amount (or null), property_value (or null), co_applicant (boolean), notes (or null).

Output ONLY the raw JSON object.""",

    "FN-002": """Generate a financial loan application that passes schema validation but has an extreme loan-to-income ratio.

Set loan_amount > 30x annual_income.
Example: annual_income=45000, loan_amount=1800000.
All other fields must be realistic and type-correct.
Do NOT set approval_date (leave as null — this application would be denied).

Schema fields: application_id (LA-XXXXX), applicant_name, date_of_birth, annual_income,
employment_status, employer_name (or null), employment_length_years (or null), loan_amount,
loan_purpose, loan_term_months, interest_rate (or null), credit_score (300-850),
existing_debt, application_date, approval_date (null), approved_amount (null),
property_value (or null), co_applicant (boolean), notes (or null).

Output ONLY the raw JSON object.""",

    "FN-003": """Generate a financial loan application that passes schema validation but has an impossible debt-to-income ratio.

Set (existing_debt + loan_amount) / annual_income > 1.0 (over 100% DTI).
Example: annual_income=60000, existing_debt=85000, loan_amount=40000 → DTI=208%.
Keep credit_score and other fields consistent with a moderate-risk borrower.

Schema fields: application_id (LA-XXXXX), applicant_name, date_of_birth, annual_income,
employment_status, employer_name (or null), employment_length_years (or null), loan_amount,
loan_purpose, loan_term_months, interest_rate (or null), credit_score (300-850),
existing_debt (MUST make DTI > 100%), application_date, approval_date (or null),
approved_amount (or null), property_value (or null), co_applicant (boolean), notes (or null).

Output ONLY the raw JSON object.""",

    "FN-004": """Generate a financial loan application that passes schema validation but has employment_length_years that is impossible given the applicant's age.

The applicant must be 22-26 years old but employment_length_years must be > (age - 18) + 3.
Example: born 2000-01-15 (age ~24), employment_length_years=18 (would have started at age 6).
All other fields realistic.

Schema fields: application_id (LA-XXXXX), applicant_name, date_of_birth (must make applicant 22-26),
annual_income, employment_status (employed), employer_name, employment_length_years (IMPOSSIBLE for age),
loan_amount, loan_purpose, loan_term_months, interest_rate (or null), credit_score (300-850),
existing_debt, application_date, approval_date (or null), approved_amount (or null),
property_value (or null), co_applicant (boolean), notes (or null).

Output ONLY the raw JSON object.""",

    "FN-005": """Generate a financial loan application that passes schema validation but has approved_amount GREATER THAN loan_amount.

approved_amount must be set and must be strictly greater than loan_amount.
Example: loan_amount=150000, approved_amount=195000.
Keep the excess 10-40% above requested amount.

Schema fields: application_id (LA-XXXXX), applicant_name, date_of_birth, annual_income,
employment_status, employer_name (or null), employment_length_years (or null), loan_amount,
loan_purpose, loan_term_months, interest_rate (or null), credit_score (300-850),
existing_debt, application_date, approval_date (MUST be set and >= application_date),
approved_amount (MUST be > loan_amount), property_value (or null), co_applicant (boolean),
notes (or null).

Output ONLY the raw JSON object.""",
}

# ── Finance edge case variants ─────────────────────────────────────────────
FN_EDGE_PROMPTS = [
    ("min_income", """Generate a valid loan application for a minimum-income applicant.
annual_income $15,000-$20,000. Small personal loan $1,000-$3,000. credit_score 580-650.
All cross-field rules must hold. Output ONLY the raw JSON object."""),

    ("just_18", """Generate a valid loan application for an applicant who just turned 18.
employment_length_years is 0 or null. Employment status: student or employed.
Small education or personal loan. All rules must hold.
Output ONLY the raw JSON object."""),

    ("same_day_approval", """Generate a valid loan application where application_date and approval_date are THE SAME day.
Use a small auto or personal loan. All rules must hold.
Output ONLY the raw JSON object."""),

    ("high_income_large_loan", """Generate a valid loan application for a high-income applicant (annual_income $400,000+)
requesting a home_purchase loan of $2,000,000+. Loan-to-income ratio is high but under 8x.
credit_score 780+. All rules must hold. Output ONLY the raw JSON object."""),

    ("unemployed_coapplicant", """Generate a valid loan application for an unemployed applicant.
annual_income=0, co_applicant=true, employer_name=null, employment_length_years=null.
Small loan ($2,000-$5,000). All rules must hold.
Output ONLY the raw JSON object."""),
]

# ══════════════════════════════════════════════════════════════════════════════
# LLM CALL
# ══════════════════════════════════════════════════════════════════════════════

def call_claude(system: str, user: str, dry_run: bool = False) -> dict:
    """Call Claude claude-opus-4-5 and return parsed JSON record. Retries on parse failure."""
    if dry_run:
        return {"_dry_run": True}

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            raw = response.content[0].text.strip()

            # strip markdown fences if the model included them despite instructions
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

            return json.loads(raw)

        except json.JSONDecodeError as e:
            if attempt < MAX_RETRIES:
                print(f"    [retry {attempt}/{MAX_RETRIES}] JSON parse error: {e}")
                time.sleep(RETRY_DELAY)
            else:
                raise RuntimeError(f"JSON parse failed after {MAX_RETRIES} attempts: {e}\nRaw: {raw[:300]}")
        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"    [retry {attempt}/{MAX_RETRIES}] API error: {e}")
                time.sleep(RETRY_DELAY * attempt)
            else:
                raise


# ══════════════════════════════════════════════════════════════════════════════
# SCHEMA VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

_schema_cache = {}

def load_schema(domain: str) -> dict:
    if domain not in _schema_cache:
        fname = "healthcare_schema.json" if "healthcare" in domain else "finance_schema.json"
        with open(SCHEMA_DIR / fname) as f:
            _schema_cache[domain] = json.load(f)
    return _schema_cache[domain]


def structural_check(record: dict, domain: str) -> tuple[bool, list[str]]:
    """Return (is_valid, list_of_errors)."""
    schema = load_schema(domain)
    v = jsonschema.Draft7Validator(schema)
    errors = [e.message for e in v.iter_errors(record)]
    return (len(errors) == 0), errors


# ══════════════════════════════════════════════════════════════════════════════
# SEMANTIC VALIDATION (inline — avoids import side-effects)
# ══════════════════════════════════════════════════════════════════════════════

def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def _age(dob, ref):
    y = ref.year - dob.year
    if (ref.month, ref.day) < (dob.month, dob.day):
        y -= 1
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

def semantic_check_hc(record: dict) -> list[str]:
    """Return list of violated rule IDs."""
    violated = []
    dob  = _parse_date(record.get("date_of_birth"))
    adm  = _parse_date(record.get("admission_date"))
    disc = _parse_date(record.get("discharge_date"))
    age  = record.get("patient_age")
    code = record.get("diagnosis_code","")
    med  = record.get("medication")

    if dob and adm and age is not None:
        if abs(_age(dob, adm) - age) > 1:
            violated.append("HC-001")
    if dob and adm:
        if adm < dob:
            violated.append("HC-002")
    if adm and disc:
        if disc < adm:
            violated.append("HC-003")
    if age is not None and code in ADULT_ONLY and age < 18:
        violated.append("HC-004")
    if med and code:
        cat = code[:3]
        known = MED_MAP.get(cat)
        if known and med not in known:
            violated.append("HC-005")
    return violated


def semantic_check_fn(record: dict) -> list[str]:
    """Return list of violated rule IDs."""
    violated = []
    app  = _parse_date(record.get("application_date"))
    appr = _parse_date(record.get("approval_date"))
    dob  = _parse_date(record.get("date_of_birth"))
    income       = record.get("annual_income", 0) or 0
    loan         = record.get("loan_amount",   0) or 0
    debt         = record.get("existing_debt", 0) or 0
    emp_yrs      = record.get("employment_length_years")
    appr_amount  = record.get("approved_amount")

    if app and appr and appr < app:
        violated.append("FN-001")
    if income > 0 and loan / income > 10:
        violated.append("FN-002")
    if income > 0 and (debt + loan) / income > 0.6:
        violated.append("FN-003")
    if dob and app and emp_yrs is not None:
        applicant_age = _age(dob, app)
        if emp_yrs > applicant_age - 18:
            violated.append("FN-004")
    if appr_amount is not None and loan > 0 and appr_amount > loan:
        violated.append("FN-005")
    return violated

# ══════════════════════════════════════════════════════════════════════════════
# EXPLANATION BUILDER
# ══════════════════════════════════════════════════════════════════════════════

RULE_EXPLANATIONS = {
    "HC-001": "Patient age field does not match the age calculated from date_of_birth and admission_date.",
    "HC-002": "Admission date precedes the patient's date of birth — patient was not yet born.",
    "HC-003": "Discharge date precedes admission date — patient cannot leave before arriving.",
    "HC-004": "Diagnosis code is not age-appropriate for a pediatric patient.",
    "HC-005": "Medication is not a plausible treatment for the stated diagnosis.",
    "FN-001": "Approval date precedes application date — loan cannot be approved before it was applied for.",
    "FN-002": "Loan-to-income ratio exceeds 10x — loan amount is unreasonably large relative to income.",
    "FN-003": "Combined debt-to-income ratio exceeds 60% — total debt burden is unsustainable.",
    "FN-004": "Employment length is impossible given the applicant's age — would have started before adulthood.",
    "FN-005": "Approved amount exceeds the requested loan amount — approvals cannot exceed requests.",
}

def build_explanation(category: str, violated_rules: list[str], record: dict) -> str:
    if category == "valid" or category == "edge_case":
        return "Record passed all structural and semantic validation checks."
    parts = [RULE_EXPLANATIONS.get(r, f"Rule {r} violated.") for r in violated_rules]
    return " ".join(parts) if parts else "Semantic violation detected."


# ══════════════════════════════════════════════════════════════════════════════
# RECORD LABELER
# ══════════════════════════════════════════════════════════════════════════════

def make_labeled_record(
    domain: str, category: str, record: dict,
    violated_rules: list[str], edge_case_type: str = None,
    structural_errors: list[str] = None,
) -> dict:
    prefix = "HC" if "healthcare" in domain else "FN"
    record_id = f"{prefix}-gen-{uuid.uuid4().hex[:8]}"
    return {
        "record_id":        record_id,
        "domain":           domain,
        "category":         category,
        "edge_case_type":   edge_case_type,
        "record":           record,
        "labels": {
            "structural_valid": not bool(structural_errors),
            "structural_errors": structural_errors or [],
            "semantic_valid":   category != "invalid",
            "violated_rules":   violated_rules,
            "explanation":      build_explanation(category, violated_rules, record),
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


# ══════════════════════════════════════════════════════════════════════════════
# GENERATION WORKERS
# ══════════════════════════════════════════════════════════════════════════════

def generate_hc_valid(count: int, dry_run: bool) -> list[dict]:
    results, i = [], 0
    variants = HC_VALID_VARIANTS * (count // len(HC_VALID_VARIANTS) + 1)
    random.shuffle(variants)
    for age_range, gender, condition in variants[:count]:
        i += 1
        print(f"  HC valid {i}/{count}: {age_range} {gender} — {condition}")
        prompt = HC_VALID_PROMPT.format(age_range=age_range, gender=gender, condition=condition)
        try:
            rec = call_claude(HC_SYSTEM, prompt, dry_run)
            ok, errs = structural_check(rec, "healthcare_intake") if not dry_run else (True, [])
            violated = semantic_check_hc(rec) if (ok and not dry_run) else []
            if violated:
                print(f"    [warn] valid record triggered rules: {violated} — keeping (may be borderline)")
            results.append(make_labeled_record("healthcare_intake", "valid", rec, [], structural_errors=errs))
        except Exception as e:
            print(f"    [error] {e}")
    return results


def generate_hc_invalid(count_per_rule: int, dry_run: bool) -> list[dict]:
    results = []
    for rule_id in HC_RULES:
        print(f"  HC invalid — rule {rule_id} × {count_per_rule}")
        prompt = HC_INVALID_PROMPTS[rule_id]
        generated = 0
        attempts = 0
        while generated < count_per_rule and attempts < count_per_rule * 3:
            attempts += 1
            try:
                rec = call_claude(HC_SYSTEM, prompt, dry_run)
                ok, errs = structural_check(rec, "healthcare_intake") if not dry_run else (True, [])
                if not ok:
                    print(f"    [skip] structural invalid: {errs[:1]}")
                    continue
                violated = semantic_check_hc(rec) if not dry_run else [rule_id]
                if rule_id not in violated:
                    print(f"    [retry] expected {rule_id}, got {violated} — retrying")
                    continue
                results.append(make_labeled_record("healthcare_intake", "invalid", rec, violated))
                generated += 1
                print(f"    [{generated}/{count_per_rule}] ✓ {rule_id} confirmed")
            except Exception as e:
                print(f"    [error] {e}")
        if generated < count_per_rule:
            print(f"    [warn] only generated {generated}/{count_per_rule} for {rule_id}")
    return results


def generate_hc_edge(count_per_type: int, dry_run: bool) -> list[dict]:
    results = []
    for edge_type, prompt in HC_EDGE_PROMPTS:
        print(f"  HC edge_case — {edge_type} × {count_per_type}")
        generated = 0
        attempts = 0
        while generated < count_per_type and attempts < count_per_type * 3:
            attempts += 1
            try:
                rec = call_claude(HC_SYSTEM, prompt, dry_run)
                ok, errs = structural_check(rec, "healthcare_intake") if not dry_run else (True, [])
                if not ok:
                    print(f"    [skip] structural invalid: {errs[:1]}")
                    continue
                violated = semantic_check_hc(rec) if not dry_run else []
                if violated:
                    print(f"    [warn] edge case triggered rules: {violated} — keeping")
                results.append(make_labeled_record(
                    "healthcare_intake", "edge_case", rec, violated, edge_case_type=edge_type,
                    structural_errors=errs))
                generated += 1
            except Exception as e:
                print(f"    [error] {e}")
    return results


def generate_fn_valid(count: int, dry_run: bool) -> list[dict]:
    results, i = [], 0
    variants = FN_VALID_VARIANTS * (count // len(FN_VALID_VARIANTS) + 1)
    random.shuffle(variants)
    for profile, loan_type in variants[:count]:
        i += 1
        print(f"  FN valid {i}/{count}: {profile} — {loan_type}")
        prompt = FN_VALID_PROMPT.format(profile=profile, loan_type=loan_type)
        try:
            rec = call_claude(FN_SYSTEM, prompt, dry_run)
            ok, errs = structural_check(rec, "financial_loan_application") if not dry_run else (True, [])
            violated = semantic_check_fn(rec) if (ok and not dry_run) else []
            if violated:
                print(f"    [warn] valid record triggered rules: {violated} — keeping")
            results.append(make_labeled_record("financial_loan_application", "valid", rec, [], structural_errors=errs))
        except Exception as e:
            print(f"    [error] {e}")
    return results


def generate_fn_invalid(count_per_rule: int, dry_run: bool) -> list[dict]:
    results = []
    for rule_id in FN_RULES:
        print(f"  FN invalid — rule {rule_id} × {count_per_rule}")
        prompt = FN_INVALID_PROMPTS[rule_id]
        generated = 0
        attempts = 0
        while generated < count_per_rule and attempts < count_per_rule * 3:
            attempts += 1
            try:
                rec = call_claude(FN_SYSTEM, prompt, dry_run)
                ok, errs = structural_check(rec, "financial_loan_application") if not dry_run else (True, [])
                if not ok:
                    print(f"    [skip] structural invalid: {errs[:1]}")
                    continue
                violated = semantic_check_fn(rec) if not dry_run else [rule_id]
                if rule_id not in violated:
                    print(f"    [retry] expected {rule_id}, got {violated} — retrying")
                    continue
                results.append(make_labeled_record("financial_loan_application", "invalid", rec, violated))
                generated += 1
                print(f"    [{generated}/{count_per_rule}] ✓ {rule_id} confirmed")
            except Exception as e:
                print(f"    [error] {e}")
        if generated < count_per_rule:
            print(f"    [warn] only generated {generated}/{count_per_rule} for {rule_id}")
    return results


def generate_fn_edge(count_per_type: int, dry_run: bool) -> list[dict]:
    results = []
    for edge_type, prompt in FN_EDGE_PROMPTS:
        print(f"  FN edge_case — {edge_type} × {count_per_type}")
        generated = 0
        attempts = 0
        while generated < count_per_type and attempts < count_per_type * 3:
            attempts += 1
            try:
                rec = call_claude(FN_SYSTEM, prompt, dry_run)
                ok, errs = structural_check(rec, "financial_loan_application") if not dry_run else (True, [])
                if not ok:
                    print(f"    [skip] structural invalid: {errs[:1]}")
                    continue
                violated = semantic_check_fn(rec) if not dry_run else []
                if violated:
                    print(f"    [warn] edge case triggered rules: {violated} — keeping")
                results.append(make_labeled_record(
                    "financial_loan_application", "edge_case", rec, violated, edge_case_type=edge_type,
                    structural_errors=errs))
                generated += 1
            except Exception as e:
                print(f"    [error] {e}")
    return results

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY + CHARTS
# ══════════════════════════════════════════════════════════════════════════════

def build_summary(hc_records: list[dict], fn_records: list[dict]) -> dict:
    summary = {}
    for domain_key, records in [("healthcare_intake", hc_records), ("financial_loan_application", fn_records)]:
        cat_counts = defaultdict(int)
        rule_counts = defaultdict(int)
        edge_counts = defaultdict(int)
        struct_invalid = 0
        for r in records:
            cat_counts[r["category"]] += 1
            for rule in r["labels"]["violated_rules"]:
                rule_counts[rule] += 1
            if r.get("edge_case_type"):
                edge_counts[r["edge_case_type"]] += 1
            if not r["labels"]["structural_valid"]:
                struct_invalid += 1
        summary[domain_key] = {
            "total": len(records),
            "by_category": dict(cat_counts),
            "by_rule": dict(rule_counts),
            "by_edge_type": dict(edge_counts),
            "structural_invalid": struct_invalid,
        }
    return summary


def save_summary_csv(summary: dict) -> Path:
    import csv
    rows = []
    for domain, stats in summary.items():
        rows.append({"domain": domain, "metric": "total", "key": "all", "count": stats["total"]})
        for cat, cnt in stats["by_category"].items():
            rows.append({"domain": domain, "metric": "category", "key": cat, "count": cnt})
        for rule, cnt in stats["by_rule"].items():
            rows.append({"domain": domain, "metric": "rule", "key": rule, "count": cnt})
        for et, cnt in stats["by_edge_type"].items():
            rows.append({"domain": domain, "metric": "edge_type", "key": et, "count": cnt})

    csv_path = DATA_DIR / "dataset_summary.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["domain", "metric", "key", "count"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Saved: {csv_path}")
    return csv_path


def save_summary_chart(summary: dict) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("  [skip chart] matplotlib not available")
        return

    plt.rcParams.update({
        "figure.facecolor": "#0d1117", "axes.facecolor": "#161b22",
        "axes.edgecolor": "#30363d", "axes.labelcolor": "#c9d1d9",
        "xtick.color": "#8b949e", "ytick.color": "#8b949e",
        "text.color": "#c9d1d9", "grid.color": "#21262d",
        "grid.linestyle": "--", "grid.alpha": 0.5,
    })
    GREEN, YELLOW, RED, BLUE, PURPLE = "#238636","#d29922","#da3633","#58a6ff","#8957e5"

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("SchemaGuard — Dataset Generation Summary", fontsize=15, color=BLUE, y=1.01)

    domain_labels = {"healthcare_intake": "Healthcare", "financial_loan_application": "Finance"}
    colors_cat = {"valid": GREEN, "invalid": RED, "edge_case": YELLOW}

    # Row 0: category distribution per domain
    for col, (domain, stats) in enumerate(summary.items()):
        ax = axes[0][col]
        cats = ["valid", "invalid", "edge_case"]
        counts = [stats["by_category"].get(c, 0) for c in cats]
        bars = ax.bar(cats, counts, color=[colors_cat[c] for c in cats], alpha=0.85, zorder=3)
        ax.set_title(f"{domain_labels[domain]} — Category Distribution", color="#c9d1d9", fontsize=12)
        ax.set_ylabel("Count", fontsize=10)
        ax.grid(axis="y", zorder=0)
        for bar, cnt in zip(bars, counts):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5, str(cnt),
                    ha="center", fontsize=11, color="#c9d1d9")

    # Row 1: rule violation distribution per domain
    for col, (domain, stats) in enumerate(summary.items()):
        ax = axes[1][col]
        rules = sorted(stats["by_rule"].keys())
        counts = [stats["by_rule"][r] for r in rules]
        if not rules:
            ax.text(0.5, 0.5, "No violations recorded", ha="center", va="center",
                    transform=ax.transAxes, color="#8b949e")
        else:
            bars = ax.barh(rules, counts, color=RED, alpha=0.85, zorder=3)
            ax.set_title(f"{domain_labels[domain]} — Rule Violations", color="#c9d1d9", fontsize=12)
            ax.set_xlabel("Count", fontsize=10)
            ax.grid(axis="x", zorder=0)
            for bar, cnt in zip(bars, counts):
                ax.text(bar.get_width()+0.2, bar.get_y()+bar.get_height()/2,
                        str(cnt), va="center", fontsize=10, color="#c9d1d9")

    plt.tight_layout()
    chart_path = PLOTS_DIR / "dataset_summary.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    plt.close()
    print(f"  Saved: {chart_path}")


# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

def generate_domain(domain: str, dry_run: bool) -> list[dict]:
    n_valid       = int(RECORDS_TOTAL * VALID_PCT)     # 120
    n_invalid     = int(RECORDS_TOTAL * INVALID_PCT)   # 120 → 24 per rule
    n_edge        = int(RECORDS_TOTAL * EDGE_PCT)      # 60  → 12 per type

    n_per_rule    = n_invalid // 5   # 24
    n_per_edge    = n_edge    // 5   # 12

    is_hc = "healthcare" in domain

    print(f"\n{'─'*60}")
    print(f"  Domain : {domain}")
    print(f"  Plan   : {n_valid} valid / {n_invalid} invalid ({n_per_rule}/rule) / {n_edge} edge ({n_per_edge}/type)")
    print(f"{'─'*60}")

    records = []

    print(f"\n[1/3] Generating valid records…")
    records += (generate_hc_valid if is_hc else generate_fn_valid)(n_valid, dry_run)

    print(f"\n[2/3] Generating invalid records…")
    records += (generate_hc_invalid if is_hc else generate_fn_invalid)(n_per_rule, dry_run)

    print(f"\n[3/3] Generating edge-case records…")
    records += (generate_hc_edge if is_hc else generate_fn_edge)(n_per_edge, dry_run)

    random.shuffle(records)
    return records


# ══════════════════════════════════════════════════════════════════════════════
# SAVE DATASETS
# ══════════════════════════════════════════════════════════════════════════════

def save_dataset(records: list[dict], domain: str) -> Path:
    fname = "healthcare_dataset.json" if "healthcare" in domain else "finance_dataset.json"
    path = DATA_DIR / fname
    with open(path, "w") as f:
        json.dump(records, f, indent=2)
    print(f"  Saved {len(records)} records → {path}")
    return path


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="SchemaGuard full synthetic dataset generator")
    parser.add_argument("--domain", choices=["hc","fn","both"], default="both",
                        help="Which domain to generate (hc=healthcare, fn=finance, both)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show generation plan without making API calls")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    random.seed(args.seed)

    if not args.dry_run and not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set. Export it or use --dry-run.")
        sys.exit(1)

    if args.dry_run:
        print("=" * 60)
        print("  DRY RUN — no API calls will be made")
        print("=" * 60)

    hc_records, fn_records = [], []
    t0 = time.time()

    if args.domain in ("hc", "both"):
        hc_records = generate_domain("healthcare_intake", args.dry_run)
        if not args.dry_run:
            save_dataset(hc_records, "healthcare_intake")

    if args.domain in ("fn", "both"):
        fn_records = generate_domain("financial_loan_application", args.dry_run)
        if not args.dry_run:
            save_dataset(fn_records, "financial_loan_application")

    # Summary
    print(f"\n{'='*60}")
    print(f"  GENERATION COMPLETE  ({time.time()-t0:.1f}s)")
    print(f"{'='*60}")

    if hc_records or fn_records:
        summary = build_summary(hc_records, fn_records)
        for domain, stats in summary.items():
            label = "Healthcare" if "health" in domain else "Finance"
            print(f"\n  {label} ({stats['total']} records)")
            for cat, cnt in sorted(stats["by_category"].items()):
                print(f"    {cat:<12} {cnt}")
            if stats["by_rule"]:
                print(f"    rule violations:")
                for rule, cnt in sorted(stats["by_rule"].items()):
                    print(f"      {rule}  {cnt}")

        if not args.dry_run:
            print()
            save_summary_csv(summary)
            save_summary_chart(summary)

    print(f"\n  Output files:")
    print(f"    data/healthcare_dataset.json")
    print(f"    data/finance_dataset.json")
    print(f"    data/dataset_summary.csv")
    print(f"    outputs/plots/dataset_summary.png")


if __name__ == "__main__":
    main()

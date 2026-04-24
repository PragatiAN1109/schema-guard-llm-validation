"""
SchemaGuard — Healthcare Semantic Rules

Cross-field validation rules for healthcare intake records.
Each rule is registered with the global RuleRegistry.
"""

from datetime import datetime, date
from rules.rule_registry import register_rule, RuleResult


def _parse_date(date_str: str | None) -> date | None:
    """Parse ISO date string to date object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _age_from_dates(dob: date, ref: date) -> int:
    """Calculate age in years from date of birth and reference date."""
    years = ref.year - dob.year
    if (ref.month, ref.day) < (dob.month, dob.day):
        years -= 1
    return years


# --- HC-001: Patient age matches date_of_birth vs admission_date ---

@register_rule(
    domain="healthcare_intake",
    rule_id="HC-001",
    rule_name="age_matches_dates",
    severity="critical",
    fields=["patient_age", "date_of_birth", "admission_date"],
)
def check_age_matches_dates(record: dict) -> RuleResult:
    dob = _parse_date(record.get("date_of_birth"))
    admission = _parse_date(record.get("admission_date"))
    stated_age = record.get("patient_age")

    if dob is None or admission is None or stated_age is None:
        return RuleResult(
            rule_id="HC-001",
            rule_name="age_matches_dates",
            passed=True,
            severity="critical",
            fields=["patient_age", "date_of_birth", "admission_date"],
            message="",
        )

    computed_age = _age_from_dates(dob, admission)
    passed = abs(computed_age - stated_age) <= 1  # allow 1-year tolerance for birthday boundary

    return RuleResult(
        rule_id="HC-001",
        rule_name="age_matches_dates",
        passed=passed,
        severity="critical",
        fields=["patient_age", "date_of_birth", "admission_date"],
        message="" if passed else (
            f"Stated age ({stated_age}) does not match computed age ({computed_age}) "
            f"from date_of_birth ({record['date_of_birth']}) and admission_date ({record['admission_date']})"
        ),
    )


# --- HC-002: Admission date is after date of birth ---

@register_rule(
    domain="healthcare_intake",
    rule_id="HC-002",
    rule_name="admission_after_birth",
    severity="critical",
    fields=["date_of_birth", "admission_date"],
)
def check_admission_after_birth(record: dict) -> RuleResult:
    dob = _parse_date(record.get("date_of_birth"))
    admission = _parse_date(record.get("admission_date"))

    if dob is None or admission is None:
        return RuleResult(
            rule_id="HC-002", rule_name="admission_after_birth",
            passed=True, severity="critical",
            fields=["date_of_birth", "admission_date"], message="",
        )

    passed = admission >= dob
    return RuleResult(
        rule_id="HC-002",
        rule_name="admission_after_birth",
        passed=passed,
        severity="critical",
        fields=["date_of_birth", "admission_date"],
        message="" if passed else (
            f"Admission date ({record['admission_date']}) is before date of birth ({record['date_of_birth']})"
        ),
    )


# --- HC-003: Discharge date is after admission date ---

@register_rule(
    domain="healthcare_intake",
    rule_id="HC-003",
    rule_name="discharge_after_admission",
    severity="critical",
    fields=["admission_date", "discharge_date"],
)
def check_discharge_after_admission(record: dict) -> RuleResult:
    admission = _parse_date(record.get("admission_date"))
    discharge = _parse_date(record.get("discharge_date"))

    if admission is None or discharge is None:
        return RuleResult(
            rule_id="HC-003", rule_name="discharge_after_admission",
            passed=True, severity="critical",
            fields=["admission_date", "discharge_date"], message="",
        )

    passed = discharge >= admission
    return RuleResult(
        rule_id="HC-003",
        rule_name="discharge_after_admission",
        passed=passed,
        severity="critical",
        fields=["admission_date", "discharge_date"],
        message="" if passed else (
            f"Discharge date ({record['discharge_date']}) precedes admission date ({record['admission_date']})"
        ),
    )


# --- HC-004: Age-appropriate diagnosis ---

# ICD-10 codes that are age-restricted
_ADULT_ONLY_CODES = {"M81.0", "M81.8", "I25.10", "I25.11", "E11.9", "E11.65", "N40.0", "C61"}
_PEDIATRIC_ONLY_CODES = {"P07.3", "P59.9", "P22.0", "P36.9"}

@register_rule(
    domain="healthcare_intake",
    rule_id="HC-004",
    rule_name="age_appropriate_diagnosis",
    severity="warning",
    fields=["patient_age", "diagnosis_code"],
)
def check_age_appropriate_diagnosis(record: dict) -> RuleResult:
    age = record.get("patient_age")
    code = record.get("diagnosis_code", "")

    if age is None:
        return RuleResult(
            rule_id="HC-004", rule_name="age_appropriate_diagnosis",
            passed=True, severity="warning",
            fields=["patient_age", "diagnosis_code"], message="",
        )

    violation = None
    if code in _ADULT_ONLY_CODES and age < 18:
        violation = f"Diagnosis {code} is adult-only but patient age is {age}"
    elif code in _PEDIATRIC_ONLY_CODES and age > 5:
        violation = f"Diagnosis {code} is neonatal/pediatric but patient age is {age}"

    return RuleResult(
        rule_id="HC-004",
        rule_name="age_appropriate_diagnosis",
        passed=violation is None,
        severity="warning",
        fields=["patient_age", "diagnosis_code"],
        message=violation or "",
    )


# --- HC-005: Medication plausibility ---

_DIAGNOSIS_MED_MAP = {
    "E11": {"Metformin", "Insulin", "Glipizide", "Sitagliptin", "Empagliflozin", "Pioglitazone"},
    "J18": {"Azithromycin", "Amoxicillin", "Levofloxacin", "Ceftriaxone", "Doxycycline"},
    "J06": {"Amoxicillin", "Ibuprofen", "Acetaminophen"},
    "I10": {"Lisinopril", "Amlodipine", "Losartan", "Hydrochlorothiazide", "Metoprolol"},
    "I25": {"Atorvastatin", "Aspirin", "Clopidogrel", "Metoprolol", "Lisinopril"},
    "N39": {"Ciprofloxacin", "Nitrofurantoin", "Trimethoprim", "Amoxicillin"},
    "K21": {"Omeprazole", "Pantoprazole", "Esomeprazole", "Ranitidine", "Famotidine"},
}

@register_rule(
    domain="healthcare_intake",
    rule_id="HC-005",
    rule_name="medication_plausibility",
    severity="warning",
    fields=["diagnosis_code", "medication"],
)
def check_medication_plausibility(record: dict) -> RuleResult:
    code = record.get("diagnosis_code", "")
    med = record.get("medication")

    if not med or not code:
        return RuleResult(
            rule_id="HC-005", rule_name="medication_plausibility",
            passed=True, severity="warning",
            fields=["diagnosis_code", "medication"], message="",
        )

    # Match on ICD-10 category (first 3 chars)
    category = code[:3]
    known_meds = _DIAGNOSIS_MED_MAP.get(category)

    if known_meds is None:
        # Unknown category — can't validate, pass by default
        return RuleResult(
            rule_id="HC-005", rule_name="medication_plausibility",
            passed=True, severity="warning",
            fields=["diagnosis_code", "medication"], message="",
        )

    passed = med in known_meds
    return RuleResult(
        rule_id="HC-005",
        rule_name="medication_plausibility",
        passed=passed,
        severity="warning",
        fields=["diagnosis_code", "medication"],
        message="" if passed else (
            f"Medication '{med}' is not a typical treatment for diagnosis category {category} ({code})"
        ),
    )

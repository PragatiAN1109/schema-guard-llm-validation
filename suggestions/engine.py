"""
SchemaGuard — Correction Suggestion Engine
==========================================
For each violated rule, produces:
  - field_corrections : field → suggested corrected value
  - explanation       : plain-English reason for the correction
  - how_to_fix        : step-by-step remediation instruction
  - reference         : regulation or standard being enforced
  - confidence        : how deterministic the suggestion is
    "definite"  — the exact correct value can be computed from the record
    "probable"  — a strongly-guided recommendation, but human review needed
    "manual"    — the system cannot derive the correct value; human required

Public API
----------
    from suggestions.engine import suggest_fixes

    result = suggest_fixes(record, domain, violated_rules)
    # result.suggestions  → list[RuleSuggestion]
    # result.fixed_record → dict with corrections applied
    # result.summary      → human-readable summary string
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Any


# ── data types ────────────────────────────────────────────────────────────────

@dataclass
class FieldCorrection:
    field: str
    current_value: Any
    suggested_value: Any
    note: str


@dataclass
class RuleSuggestion:
    rule_id:           str
    rule_name:         str
    severity:          str
    violation_message: str
    explanation:       str
    how_to_fix:        str
    reference:         str
    confidence:        str          # "definite" | "probable" | "manual"
    field_corrections: list[FieldCorrection]


@dataclass
class SuggestionResult:
    record_id:     str
    domain:        str
    suggestions:   list[RuleSuggestion]
    fixed_record:  dict
    summary:       str
    total_fixable: int              # count of "definite" + "probable"
    total_manual:  int              # count requiring human review


# ── date helpers ──────────────────────────────────────────────────────────────

def _parse(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(str(s).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _today() -> date:
    return datetime.utcnow().date()


def _age(dob: date, ref: date) -> int:
    y = ref.year - dob.year
    if (ref.month, ref.day) < (dob.month, dob.day):
        y -= 1
    return max(0, y)


# ── per-rule suggestion functions ─────────────────────────────────────────────

def _suggest_hc001(record: dict, violation: dict) -> RuleSuggestion:
    """HC-001: Age does not match date_of_birth + admission_date."""
    dob       = _parse(record.get("date_of_birth"))
    admission = _parse(record.get("admission_date"))
    stated    = record.get("patient_age")

    if dob and admission:
        correct_age = _age(dob, admission)
        corrections = [FieldCorrection(
            field="patient_age",
            current_value=stated,
            suggested_value=correct_age,
            note=(f"Computed from date_of_birth={record['date_of_birth']} "
                  f"and admission_date={record['admission_date']}"),
        )]
        confidence = "definite"
        fix = (f"Set patient_age to {correct_age}. "
               f"This is the exact age computed from the stored date_of_birth "
               f"({record['date_of_birth']}) at the time of admission "
               f"({record['admission_date']}).")
    else:
        corrections = [FieldCorrection(
            field="patient_age",
            current_value=stated,
            suggested_value=None,
            note="Cannot compute — date_of_birth or admission_date is missing or unparseable",
        )]
        confidence = "manual"
        fix = ("Verify date_of_birth and admission_date are valid YYYY-MM-DD dates, "
               "then recompute patient_age as the applicant's age on the admission date.")

    return RuleSuggestion(
        rule_id="HC-001", rule_name="age_matches_dates", severity="critical",
        violation_message=violation.get("message", ""),
        explanation=(
            "The stated patient_age does not match the age computed from date_of_birth "
            "and admission_date. This inconsistency can cause dosing errors, incorrect "
            "age-based treatment protocols, and billing rejections."
        ),
        how_to_fix=fix,
        reference="HL7 FHIR R4 §Patient.birthDate; CMS Conditions of Participation §482.24(c)",
        confidence=confidence,
        field_corrections=corrections,
    )


def _suggest_hc002(record: dict, violation: dict) -> RuleSuggestion:
    """HC-002: Admission date is before date_of_birth."""
    dob       = _parse(record.get("date_of_birth"))
    admission = _parse(record.get("admission_date"))

    # Determine which field is more likely wrong
    if dob and admission and dob > _today():
        # DOB is in the future — almost certainly the erroneous field
        corrections = [FieldCorrection(
            field="date_of_birth",
            current_value=record.get("date_of_birth"),
            suggested_value=None,
            note="date_of_birth is a future date — likely a data entry error",
        )]
        confidence = "manual"
        fix = ("date_of_birth is set to a future date, which is impossible. "
               "Verify the patient's birth year. Common causes: year entered as "
               "2025 instead of 1925, or MM/DD/YYYY transposed to YYYY-MM-DD incorrectly.")
    elif dob and admission:
        corrections = [
            FieldCorrection(
                field="admission_date",
                current_value=record.get("admission_date"),
                suggested_value=str(dob + timedelta(days=1)),
                note="admission_date must be on or after date_of_birth",
            )
        ]
        confidence = "probable"
        fix = ("admission_date precedes date_of_birth, which is impossible. "
               "Either the admission_date is wrong (verify the calendar date of admission) "
               "or date_of_birth is wrong (verify the patient's birth record).")
    else:
        corrections = []
        confidence = "manual"
        fix = "Verify both date_of_birth and admission_date are valid YYYY-MM-DD dates."

    return RuleSuggestion(
        rule_id="HC-002", rule_name="admission_after_birth", severity="critical",
        violation_message=violation.get("message", ""),
        explanation=(
            "A patient cannot be admitted before they were born. "
            "This error typically indicates a transposed year, a future date_of_birth, "
            "or an admission date entered for the wrong calendar year."
        ),
        how_to_fix=fix,
        reference="HL7 FHIR R4 §Patient.birthDate; Joint Commission Record of Care RC.02.01.01",
        confidence=confidence,
        field_corrections=corrections,
    )

def _suggest_hc003(record: dict, violation: dict) -> RuleSuggestion:
    """HC-003: Discharge date precedes admission date."""
    admission = _parse(record.get("admission_date"))
    discharge = _parse(record.get("discharge_date"))

    if admission and discharge and discharge < admission:
        # Suggest swapping if dates are close (likely swapped entry)
        delta_days = abs((admission - discharge).days)
        if delta_days <= 30:
            corrections = [
                FieldCorrection(
                    field="discharge_date",
                    current_value=record.get("discharge_date"),
                    suggested_value=record.get("admission_date"),
                    note="Dates appear swapped — admission and discharge values transposed",
                ),
                FieldCorrection(
                    field="admission_date",
                    current_value=record.get("admission_date"),
                    suggested_value=record.get("discharge_date"),
                    note="Dates appear swapped — admission and discharge values transposed",
                ),
            ]
            confidence = "probable"
            fix = (f"admission_date ({record['admission_date']}) and discharge_date "
                   f"({record['discharge_date']}) appear to be swapped — they are only "
                   f"{delta_days} day(s) apart. Try reversing the two values. "
                   "If the dates are not swapped, verify the source document.")
        else:
            corrections = [FieldCorrection(
                field="discharge_date",
                current_value=record.get("discharge_date"),
                suggested_value=str(admission + timedelta(days=1)),
                note="discharge_date must be on or after admission_date",
            )]
            confidence = "probable"
            fix = (f"discharge_date ({record['discharge_date']}) is before "
                   f"admission_date ({record['admission_date']}). "
                   "Verify the discharge date from the source clinical document. "
                   "For same-day discharge, set discharge_date equal to admission_date.")
    else:
        corrections = []
        confidence = "manual"
        fix = "Verify admission_date and discharge_date are valid YYYY-MM-DD dates in chronological order."

    return RuleSuggestion(
        rule_id="HC-003", rule_name="discharge_after_admission", severity="critical",
        violation_message=violation.get("message", ""),
        explanation=(
            "discharge_date must be on or after admission_date. "
            "A negative length-of-stay is clinically impossible and will cause "
            "billing rejections, DRG miscalculation, and audit failures."
        ),
        how_to_fix=fix,
        reference=(
            "CMS Conditions of Participation §482.24(c)(2)(vii); "
            "NUBC UB-04 billing form fields FL6/FL16"
        ),
        confidence=confidence,
        field_corrections=corrections,
    )


def _suggest_hc004(record: dict, violation: dict) -> RuleSuggestion:
    """HC-004: Age-inappropriate diagnosis code."""
    age  = record.get("patient_age")
    code = record.get("diagnosis_code", "")

    _ADULT_ONLY = {"M81.0", "M81.8", "I25.10", "I25.11", "E11.9", "E11.65", "N40.0", "C61"}
    _PEDS_ONLY  = {"P07.3", "P59.9", "P22.0", "P36.9"}

    if code in _ADULT_ONLY and age is not None and age < 18:
        corrections = [FieldCorrection(
            field="diagnosis_code",
            current_value=code,
            suggested_value=None,
            note=f"{code} is restricted to patients ≥18; patient_age={age}",
        )]
        fix = (f"Diagnosis code {code} is documented as adult-only (age ≥18). "
               f"The patient's age is {age}. Either: (a) verify the diagnosis — "
               f"paediatric patients rarely present with {code}; "
               f"(b) correct patient_age if it was entered incorrectly; or "
               f"(c) use the appropriate paediatric equivalent ICD-10 code.")
        confidence = "manual"
    elif code in _PEDS_ONLY and age is not None and age > 5:
        corrections = [FieldCorrection(
            field="diagnosis_code",
            current_value=code,
            suggested_value=None,
            note=f"{code} is a neonatal/paediatric code; patient_age={age}",
        )]
        fix = (f"Diagnosis code {code} is a neonatal/paediatric code typically "
               f"used for patients ≤5. The patient's age is {age}. "
               f"Verify the diagnosis and select the appropriate adult ICD-10 code.")
        confidence = "manual"
    else:
        corrections = []
        fix = "Verify diagnosis_code is appropriate for the patient's age."
        confidence = "manual"

    return RuleSuggestion(
        rule_id="HC-004", rule_name="age_appropriate_diagnosis", severity="warning",
        violation_message=violation.get("message", ""),
        explanation=(
            "Certain ICD-10 codes are age-restricted. Assigning an adult-only code "
            "to a paediatric patient (or vice versa) causes claim denials, "
            "incorrect quality-measure attribution, and may trigger fraud reviews."
        ),
        how_to_fix=fix,
        reference="ICD-10-CM Official Guidelines §Section I.C — Age/Sex Edits; CMS NCCI edits",
        confidence=confidence,
        field_corrections=corrections,
    )

def _suggest_hc005(record: dict, violation: dict) -> RuleSuggestion:
    """HC-005: Medication not plausible for diagnosis."""
    code = record.get("diagnosis_code", "")
    med  = record.get("medication", "")
    cat  = code[:3] if code else ""

    _MAP = {
        "E11": ["Metformin", "Glipizide", "Sitagliptin", "Insulin", "Empagliflozin"],
        "J18": ["Azithromycin", "Amoxicillin", "Levofloxacin", "Ceftriaxone"],
        "J06": ["Amoxicillin", "Ibuprofen", "Acetaminophen"],
        "I10": ["Lisinopril", "Amlodipine", "Losartan", "Metoprolol"],
        "I25": ["Atorvastatin", "Aspirin", "Clopidogrel", "Metoprolol"],
        "N39": ["Ciprofloxacin", "Nitrofurantoin", "Trimethoprim"],
        "K21": ["Omeprazole", "Pantoprazole", "Esomeprazole"],
    }
    known = _MAP.get(cat, [])

    corrections = [FieldCorrection(
        field="medication",
        current_value=med,
        suggested_value=known[0] if known else None,
        note=(f"Typical first-line medications for {cat} ({code}): {', '.join(known)}"
              if known else f"No medication map available for ICD-10 category {cat}"),
    )]

    return RuleSuggestion(
        rule_id="HC-005", rule_name="medication_plausibility", severity="warning",
        violation_message=violation.get("message", ""),
        explanation=(
            f"'{med}' is not a recognised treatment for diagnosis category {cat} ({code}). "
            "Medication-diagnosis mismatches can indicate data entry errors, copy-paste "
            "mistakes from a previous record, or — rarely — a genuine off-label use that "
            "should be documented explicitly."
        ),
        how_to_fix=(
            f"Verify the prescribed medication against the patient's chart for diagnosis {code}. "
            f"If the medication is correct (e.g., off-label use), add a clinical note to the record. "
            + (f"Expected first-line options: {', '.join(known[:3])}." if known else "")
        ),
        reference=(
            "ISMP Medication Safety Alert — Drug-Disease Contraindications; "
            "Joint Commission NPSG.03.04.01 (medication reconciliation)"
        ),
        confidence="probable",
        field_corrections=corrections,
    )


def _suggest_fn001(record: dict, violation: dict) -> RuleSuggestion:
    """FN-001: Approval date before application date."""
    app_date  = _parse(record.get("application_date"))
    appr_date = _parse(record.get("approval_date"))

    if app_date and appr_date and appr_date < app_date:
        delta = (app_date - appr_date).days
        if delta <= 7:
            # Likely a transposition (e.g., day/month swapped in manual entry)
            corrections = [
                FieldCorrection(
                    field="approval_date",
                    current_value=record.get("approval_date"),
                    suggested_value=record.get("application_date"),
                    note=f"Dates are {delta} day(s) apart — possible data-entry transposition",
                )
            ]
            confidence = "probable"
            fix = (f"approval_date ({record['approval_date']}) is {delta} day(s) before "
                   f"application_date ({record['application_date']}). This is likely a "
                   "day/month transposition or a clerical error. Verify the actual "
                   "approval date from the loan officer's records. If the loan is still "
                   "pending, set approval_date to null.")
        else:
            corrections = [FieldCorrection(
                field="approval_date",
                current_value=record.get("approval_date"),
                suggested_value=None,
                note="approval_date must be on or after application_date",
            )]
            confidence = "manual"
            fix = (f"approval_date ({record['approval_date']}) is {delta} days before "
                   f"application_date ({record['application_date']}). A loan cannot be "
                   "approved before it is applied for. Verify both dates from the "
                   "origination system. If the loan has not yet been decided, set "
                   "approval_date to null.")
    else:
        corrections = []
        confidence = "manual"
        fix = "Verify application_date and approval_date are valid YYYY-MM-DD dates in chronological order."

    return RuleSuggestion(
        rule_id="FN-001", rule_name="approval_after_application", severity="critical",
        violation_message=violation.get("message", ""),
        explanation=(
            "A loan cannot be approved before it is applied for. "
            "Temporal inconsistency in loan dates violates RESPA and TILA disclosure "
            "timeline requirements and may trigger regulatory audit flags."
        ),
        how_to_fix=fix,
        reference=(
            "CFPB TILA-RESPA Integrated Disclosure (TRID) §1026.19; "
            "Regulation B §1002.9 — timing of notifications"
        ),
        confidence=confidence,
        field_corrections=corrections,
    )

def _suggest_fn002(record: dict, violation: dict) -> RuleSuggestion:
    """FN-002: Loan-to-income ratio exceeds 10×."""
    income = record.get("annual_income", 0) or 0
    loan   = record.get("loan_amount",   0) or 0
    MAX_LTI = 10.0

    if income > 0:
        ratio      = loan / income
        max_loan   = int(income * MAX_LTI)
        corrections = [FieldCorrection(
            field="loan_amount",
            current_value=loan,
            suggested_value=max_loan,
            note=f"Maximum loan at {MAX_LTI}× income (${income:,.0f}) = ${max_loan:,.0f}",
        )]
        confidence = "definite"
        fix = (f"Current ratio is {ratio:.1f}× (${loan:,.0f} loan / "
               f"${income:,.0f} income). The maximum allowed is {MAX_LTI}×. "
               f"Either reduce loan_amount to ≤${max_loan:,.0f}, or verify that "
               "annual_income reflects all qualifying income sources (co-applicant, "
               "rental income, bonuses). If a co-applicant exists, set co_applicant=true "
               "and add their income to annual_income.")
    else:
        corrections = [FieldCorrection(
            field="annual_income",
            current_value=income,
            suggested_value=None,
            note="annual_income is zero or missing — cannot compute max loan",
        )]
        confidence = "manual"
        fix = ("annual_income is 0 or missing. Verify the applicant's income "
               "documentation (W-2, pay stubs, tax returns) and update the field.")

    return RuleSuggestion(
        rule_id="FN-002", rule_name="loan_to_income_ratio", severity="critical",
        violation_message=violation.get("message", ""),
        explanation=(
            "The loan-to-income ratio exceeds the 10× threshold. "
            "Extreme LTI ratios indicate the applicant cannot service the debt "
            "from income alone and violate CFPB Ability-to-Repay (ATR) standards, "
            "making the loan ineligible for QM safe-harbour protection."
        ),
        how_to_fix=fix,
        reference=(
            "CFPB Regulation Z §1026.43(c) — Ability-to-Repay; "
            "Fannie Mae Selling Guide B3-6-02 (debt-to-income ratios)"
        ),
        confidence=confidence,
        field_corrections=corrections,
    )


def _suggest_fn003(record: dict, violation: dict) -> RuleSuggestion:
    """FN-003: Existing debt-to-income ratio exceeds 60%."""
    income = record.get("annual_income", 0) or 0
    debt   = record.get("existing_debt",  0) or 0
    MAX_DTI = 0.60

    if income > 0:
        dti        = debt / income
        max_debt   = int(income * MAX_DTI)
        corrections = [FieldCorrection(
            field="existing_debt",
            current_value=debt,
            suggested_value=max_debt,
            note=(f"Maximum existing_debt at {MAX_DTI:.0%} DTI "
                  f"(income ${income:,.0f}) = ${max_debt:,.0f}"),
        )]
        confidence = "probable"
        fix = (f"existing_debt (${debt:,.0f}) is {dti:.0%} of annual_income "
               f"(${income:,.0f}), exceeding the {MAX_DTI:.0%} warning threshold. "
               "This is a warning, not a hard block. Options: "
               "(1) verify that existing_debt only includes monthly obligations × 12 "
               "(not one-time balances); "
               "(2) check whether debt consolidation or payoff is planned before closing; "
               "(3) flag for manual underwriter review.")
    else:
        corrections = []
        confidence = "manual"
        fix = "Verify annual_income and existing_debt values from income/liability documentation."

    return RuleSuggestion(
        rule_id="FN-003", rule_name="debt_to_income_ratio", severity="warning",
        violation_message=violation.get("message", ""),
        explanation=(
            f"Existing debt is {(debt/income*100):.1f}% of annual income, "
            f"above the {MAX_DTI:.0%} warning level. "
            "High DTI is the leading predictor of default. This record should "
            "receive manual underwriter review before proceeding."
        ) if income > 0 else "Debt-to-income cannot be evaluated — income is missing.",
        how_to_fix=fix,
        reference=(
            "CFPB QM Standard — Back-End DTI ≤43% for Safe Harbour; "
            "Fannie Mae DU DTI limit §B3-6-02"
        ),
        confidence=confidence,
        field_corrections=corrections,
    )


def _suggest_fn004(record: dict, violation: dict) -> RuleSuggestion:
    """FN-004: Employment length impossible for applicant age."""
    emp   = record.get("employment_length_years")
    dob   = _parse(record.get("date_of_birth"))
    app   = _parse(record.get("application_date")) or _today()
    MIN_W = 16

    if dob:
        age     = _age(dob, app)
        max_emp = max(0, age - MIN_W)
        corrections = [FieldCorrection(
            field="employment_length_years",
            current_value=emp,
            suggested_value=max_emp,
            note=(f"Applicant is {age} years old; "
                  f"max employment since age {MIN_W} = {max_emp} years"),
        )]
        confidence = "definite"
        fix = (f"employment_length_years ({emp}) exceeds the maximum possible "
               f"for an applicant aged {age} (max: {max_emp} years, assuming "
               f"work starts at age {MIN_W}). "
               "Correct the value to reflect verified employment history. "
               "If the applicant has had multiple employers, use the total "
               "cumulative years, capped at the computed maximum.")
    else:
        corrections = [FieldCorrection(
            field="employment_length_years",
            current_value=emp,
            suggested_value=None,
            note="Cannot compute maximum without a valid date_of_birth",
        )]
        confidence = "manual"
        fix = ("Verify date_of_birth and employment_length_years from identity "
               "and employment verification documents.")

    return RuleSuggestion(
        rule_id="FN-004", rule_name="employment_length_vs_age", severity="critical",
        violation_message=violation.get("message", ""),
        explanation=(
            "employment_length_years exceeds what is possible given the applicant's age. "
            "This typically indicates a data entry error (e.g., total career years instead "
            "of current employer tenure) or identity fraud (age and employment don't match)."
        ),
        how_to_fix=fix,
        reference=(
            "FLSA Child Labour Provisions §29 CFR Part 570 (minimum working age 16); "
            "CFPB ATR §1026.43(c)(3) — employment income verification"
        ),
        confidence=confidence,
        field_corrections=corrections,
    )


def _suggest_fn005(record: dict, violation: dict) -> RuleSuggestion:
    """FN-005: Approved amount exceeds requested loan amount."""
    approved  = record.get("approved_amount", 0) or 0
    requested = record.get("loan_amount",     0) or 0
    excess    = approved - requested

    corrections = [FieldCorrection(
        field="approved_amount",
        current_value=approved,
        suggested_value=requested,
        note=f"approved_amount must be ≤ loan_amount (${requested:,.0f}); excess = ${excess:,.0f}",
    )]

    return RuleSuggestion(
        rule_id="FN-005", rule_name="approved_within_requested", severity="critical",
        violation_message=violation.get("message", ""),
        explanation=(
            f"approved_amount (${approved:,.0f}) exceeds the requested "
            f"loan_amount (${requested:,.0f}) by ${excess:,.0f}. "
            "A lender cannot approve more than was requested without issuing "
            "a counter-offer notice. This is a RESPA/TILA disclosure violation."
        ),
        how_to_fix=(
            f"Set approved_amount to ≤${requested:,.0f} (the requested loan_amount). "
            f"If the lender intends to offer more than requested "
            f"(e.g., offering ${approved:,.0f} when only ${requested:,.0f} was asked), "
            "this requires a separate counter-offer disclosure under Regulation B §1002.9."
        ),
        reference=(
            "CFPB Regulation B (ECOA) §1002.9 — counter-offer notification; "
            "RESPA §12 CFR Part 1024 — settlement cost disclosures"
        ),
        confidence="definite",
        field_corrections=corrections,
    )


# ── rule dispatcher ───────────────────────────────────────────────────────────

_HANDLERS = {
    "HC-001": _suggest_hc001,
    "HC-002": _suggest_hc002,
    "HC-003": _suggest_hc003,
    "HC-004": _suggest_hc004,
    "HC-005": _suggest_hc005,
    "FN-001": _suggest_fn001,
    "FN-002": _suggest_fn002,
    "FN-003": _suggest_fn003,
    "FN-004": _suggest_fn004,
    "FN-005": _suggest_fn005,
}


def _apply_corrections(record: dict, suggestions: list[RuleSuggestion]) -> dict:
    """Return a shallow copy of the record with all definite corrections applied."""
    fixed = dict(record)
    for sug in suggestions:
        if sug.confidence == "definite":
            for corr in sug.field_corrections:
                if corr.suggested_value is not None:
                    fixed[corr.field] = corr.suggested_value
    return fixed


def _build_summary(suggestions: list[RuleSuggestion], domain: str) -> str:
    if not suggestions:
        return "No violations found — record is compliant."
    n_def  = sum(1 for s in suggestions if s.confidence == "definite")
    n_prob = sum(1 for s in suggestions if s.confidence == "probable")
    n_man  = sum(1 for s in suggestions if s.confidence == "manual")
    parts  = [f"{len(suggestions)} rule violation(s) found."]
    if n_def:
        parts.append(f"{n_def} can be auto-corrected (exact fix computed).")
    if n_prob:
        parts.append(f"{n_prob} have a strongly-guided fix (human confirmation advised).")
    if n_man:
        parts.append(f"{n_man} require manual review (system cannot derive the correct value).")
    return " ".join(parts)


# ── public API ────────────────────────────────────────────────────────────────

def suggest_fixes(
    record:          dict,
    domain:          str,
    violated_rules:  list[dict],
    record_id:       str = "unknown",
) -> SuggestionResult:
    """
    Generate field-level correction suggestions for every violated rule.

    Args:
        record:         The original JSON record that was validated.
        domain:         "healthcare_intake" or "financial_loan_application".
        violated_rules: List of RuleResult dicts from validate_record().
        record_id:      Optional record identifier for the response.

    Returns:
        SuggestionResult with per-rule suggestions and a pre-corrected record.
    """
    suggestions: list[RuleSuggestion] = []

    for violation in violated_rules:
        rule_id = violation.get("rule_id", "")
        handler = _HANDLERS.get(rule_id)
        if handler:
            try:
                suggestions.append(handler(record, violation))
            except Exception as exc:
                # Safe fallback — never crash the suggestion layer
                suggestions.append(RuleSuggestion(
                    rule_id=rule_id,
                    rule_name=violation.get("rule_name", ""),
                    severity=violation.get("severity", "unknown"),
                    violation_message=violation.get("message", ""),
                    explanation=f"Suggestion engine error: {exc}",
                    how_to_fix="Review the record manually.",
                    reference="",
                    confidence="manual",
                    field_corrections=[],
                ))
        else:
            # Unknown rule — return a generic suggestion
            suggestions.append(RuleSuggestion(
                rule_id=rule_id,
                rule_name=violation.get("rule_name", ""),
                severity=violation.get("severity", "unknown"),
                violation_message=violation.get("message", ""),
                explanation=f"Rule {rule_id} violated: {violation.get('message','')}",
                how_to_fix=(
                    f"Review the fields [{', '.join(violation.get('fields', []))}] "
                    "and correct the values according to domain requirements."
                ),
                reference="",
                confidence="manual",
                field_corrections=[
                    FieldCorrection(
                        field=f,
                        current_value=record.get(f),
                        suggested_value=None,
                        note="Manual correction required",
                    )
                    for f in violation.get("fields", [])
                ],
            ))

    fixed_record = _apply_corrections(record, suggestions)
    n_fixable    = sum(1 for s in suggestions if s.confidence in ("definite", "probable"))
    n_manual     = sum(1 for s in suggestions if s.confidence == "manual")

    return SuggestionResult(
        record_id=record_id,
        domain=domain,
        suggestions=suggestions,
        fixed_record=fixed_record,
        summary=_build_summary(suggestions, domain),
        total_fixable=n_fixable,
        total_manual=n_manual,
    )

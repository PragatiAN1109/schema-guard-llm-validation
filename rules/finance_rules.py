"""
SchemaGuard — Finance Semantic Rules

Cross-field validation rules for financial loan application records.
Each rule is registered with the global RuleRegistry.
"""

from datetime import datetime, date
from rules.rule_registry import register_rule, RuleResult


def _parse_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _age_from_dates(dob: date, ref: date) -> int:
    years = ref.year - dob.year
    if (ref.month, ref.day) < (dob.month, dob.day):
        years -= 1
    return years


# --- FN-001: Approval date after application date ---

@register_rule(
    domain="financial_loan_application",
    rule_id="FN-001",
    rule_name="approval_after_application",
    severity="critical",
    fields=["application_date", "approval_date"],
)
def check_approval_after_application(record: dict) -> RuleResult:
    app_date = _parse_date(record.get("application_date"))
    appr_date = _parse_date(record.get("approval_date"))

    if app_date is None or appr_date is None:
        return RuleResult(
            rule_id="FN-001", rule_name="approval_after_application",
            passed=True, severity="critical",
            fields=["application_date", "approval_date"], message="",
        )

    passed = appr_date >= app_date
    return RuleResult(
        rule_id="FN-001",
        rule_name="approval_after_application",
        passed=passed,
        severity="critical",
        fields=["application_date", "approval_date"],
        message="" if passed else (
            f"Approval date ({record['approval_date']}) is before "
            f"application date ({record['application_date']})"
        ),
    )


# --- FN-002: Loan-to-income ratio ---

MAX_LOAN_TO_INCOME = 10.0  # 10x annual income

@register_rule(
    domain="financial_loan_application",
    rule_id="FN-002",
    rule_name="loan_to_income_ratio",
    severity="critical",
    fields=["loan_amount", "annual_income"],
)
def check_loan_to_income(record: dict) -> RuleResult:
    income = record.get("annual_income", 0)
    loan = record.get("loan_amount", 0)

    if income <= 0:
        return RuleResult(
            rule_id="FN-002", rule_name="loan_to_income_ratio",
            passed=True, severity="critical",
            fields=["loan_amount", "annual_income"], message="",
        )

    ratio = loan / income
    passed = ratio <= MAX_LOAN_TO_INCOME
    return RuleResult(
        rule_id="FN-002",
        rule_name="loan_to_income_ratio",
        passed=passed,
        severity="critical",
        fields=["loan_amount", "annual_income"],
        message="" if passed else (
            f"Loan amount (${loan:,.0f}) is {ratio:.1f}x annual income (${income:,.0f}), "
            f"exceeds {MAX_LOAN_TO_INCOME}x limit"
        ),
    )


# --- FN-003: Debt-to-income ratio ---
# Compares existing_debt (pre-existing obligations) against annual_income.
# The loan_amount itself is excluded — this checks whether the applicant
# already carries too much debt before the new loan is factored in.

MAX_DTI_RATIO = 0.60  # 60% existing-debt-to-income

@register_rule(
    domain="financial_loan_application",
    rule_id="FN-003",
    rule_name="debt_to_income_ratio",
    severity="warning",
    fields=["existing_debt", "annual_income"],
)
def check_dti_ratio(record: dict) -> RuleResult:
    income = record.get("annual_income", 0)
    debt = record.get("existing_debt", 0)

    if income <= 0 or debt <= 0:
        return RuleResult(
            rule_id="FN-003", rule_name="debt_to_income_ratio",
            passed=True, severity="warning",
            fields=["existing_debt", "annual_income"], message="",
        )

    dti = debt / income
    passed = dti <= MAX_DTI_RATIO

    return RuleResult(
        rule_id="FN-003",
        rule_name="debt_to_income_ratio",
        passed=passed,
        severity="warning",
        fields=["existing_debt", "annual_income"],
        message="" if passed else (
            f"Existing debt (${debt:,.0f}) is {dti:.0%} of annual income (${income:,.0f}), "
            f"exceeds {MAX_DTI_RATIO:.0%} threshold"
        ),
    )


# --- FN-004: Employment length vs age ---

MIN_WORKING_AGE = 16

@register_rule(
    domain="financial_loan_application",
    rule_id="FN-004",
    rule_name="employment_length_vs_age",
    severity="critical",
    fields=["employment_length_years", "date_of_birth", "application_date"],
)
def check_employment_vs_age(record: dict) -> RuleResult:
    emp_years = record.get("employment_length_years")
    dob = _parse_date(record.get("date_of_birth"))
    app_date = _parse_date(record.get("application_date"))

    if emp_years is None or dob is None or app_date is None:
        return RuleResult(
            rule_id="FN-004", rule_name="employment_length_vs_age",
            passed=True, severity="critical",
            fields=["employment_length_years", "date_of_birth", "application_date"],
            message="",
        )

    age = _age_from_dates(dob, app_date)
    max_possible_employment = age - MIN_WORKING_AGE
    passed = emp_years <= max_possible_employment

    return RuleResult(
        rule_id="FN-004",
        rule_name="employment_length_vs_age",
        passed=passed,
        severity="critical",
        fields=["employment_length_years", "date_of_birth", "application_date"],
        message="" if passed else (
            f"Employment length ({emp_years} years) is impossible for applicant age {age} "
            f"(max possible: {max_possible_employment} years, assuming work starts at {MIN_WORKING_AGE})"
        ),
    )


# --- FN-005: Approved amount does not exceed requested ---

@register_rule(
    domain="financial_loan_application",
    rule_id="FN-005",
    rule_name="approved_within_requested",
    severity="critical",
    fields=["approved_amount", "loan_amount"],
)
def check_approved_within_requested(record: dict) -> RuleResult:
    approved = record.get("approved_amount")
    requested = record.get("loan_amount", 0)

    if approved is None:
        return RuleResult(
            rule_id="FN-005", rule_name="approved_within_requested",
            passed=True, severity="critical",
            fields=["approved_amount", "loan_amount"], message="",
        )

    passed = approved <= requested
    return RuleResult(
        rule_id="FN-005",
        rule_name="approved_within_requested",
        passed=passed,
        severity="critical",
        fields=["approved_amount", "loan_amount"],
        message="" if passed else (
            f"Approved amount (${approved:,.0f}) exceeds requested loan amount (${requested:,.0f})"
        ),
    )

"""
SchemaGuard — Explanation Builder

Converts validation results into clean, human-readable explanation strings.
Handles structural errors, semantic violations, and combined failure summaries.
"""


def build_explanation(
    structural_result: dict,
    semantic_result: dict,
    decision: str,
    record_id: str = None,
) -> str:
    """
    Build a readable explanation from full validation results.

    Produces a natural-language summary suitable for end-user display.
    """
    prefix = f"Record {record_id}: " if record_id else ""

    # All clear
    if structural_result["valid"] and semantic_result.get("valid", True):
        return f"{prefix}Passed all validation checks. No issues found."

    parts = []

    # Structural failures
    if not structural_result["valid"]:
        n = len(structural_result.get("errors", []))
        parts.append(f"failed structural validation with {n} error{'s' if n != 1 else ''}")
        for err in structural_result.get("errors", [])[:3]:
            parts.append(f"field '{err['field']}' — {err['message']}")
        if n > 3:
            parts.append(f"and {n - 3} additional structural error{'s' if n - 3 != 1 else ''}")

    # Semantic violations
    violations = semantic_result.get("violations", [])
    if violations:
        critical = [v for v in violations if v["severity"] == "critical"]
        warnings = [v for v in violations if v["severity"] == "warning"]

        if critical:
            critical_msgs = [_violation_sentence(v) for v in critical]
            parts.append("Critical issues: " + "; ".join(critical_msgs))

        if warnings:
            warning_msgs = [_violation_sentence(v) for v in warnings]
            parts.append("Warnings: " + "; ".join(warning_msgs))

    # Assemble
    explanation = f"{prefix}Record failed validation. " + ". ".join(parts) + "."

    # Decision context
    decision_text = {
        "quarantined": " This record has been quarantined and should not be used downstream.",
        "flagged": " This record has been flagged for human review.",
        "trusted": "",
    }
    explanation += decision_text.get(decision, "")

    return explanation


def explain_single_violation(violation: dict) -> str:
    """Convert one rule violation into a standalone sentence."""
    return _violation_sentence(violation)


def explain_violations_list(violations: list[dict]) -> list[str]:
    """Convert a list of violations into a list of explanation sentences."""
    return [_violation_sentence(v) for v in violations]


def _violation_sentence(v: dict) -> str:
    """Format a single violation as a readable phrase."""
    fields_str = ", ".join(v.get("fields", []))
    msg = v.get("message", "")
    rule_name = v.get("rule_name", v.get("rule_id", "unknown"))

    if msg:
        return f"{rule_name} ({fields_str}): {msg}"
    return f"{rule_name} — violation on fields: {fields_str}"

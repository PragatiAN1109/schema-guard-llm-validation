"""
SchemaGuard — Semantic Validator

Runs all registered semantic rules for a domain against a record.
"""

from rules import registry
from rules.rule_registry import RuleResult


def validate_semantics(record: dict, domain: str) -> dict:
    """
    Run all semantic rules for a domain against a record.

    Returns:
        {
            "valid": bool,
            "rules_evaluated": int,
            "violations": [RuleResult],  # only failed rules
            "all_results": [RuleResult], # all rule outcomes
        }
    """
    results = registry.run_all(domain, record)
    violations = [r for r in results if not r["passed"]]

    return {
        "valid": len(violations) == 0,
        "rules_evaluated": len(results),
        "violations": violations,
        "all_results": results,
    }

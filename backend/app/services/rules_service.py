"""
Rules Service — lists all registered semantic rules from the existing engine.
"""

from rules.rule_registry import registry


def list_all_rules() -> dict:
    """Return all rules grouped by domain."""
    domains = {}
    for domain in ["healthcare_intake", "financial_loan_application"]:
        rules = registry.get_rules(domain)
        domains[domain] = [
            {
                "rule_id": r["rule_id"],
                "rule_name": r["rule_name"],
                "severity": r["severity"],
                "fields": r["fields"],
            }
            for r in rules
        ]
    return {"domains": domains, "total_rules": sum(len(v) for v in domains.values())}


def get_rules_for_domain(domain: str) -> list[dict]:
    """Return rules for a specific domain."""
    rules = registry.get_rules(domain)
    return [
        {
            "rule_id": r["rule_id"],
            "rule_name": r["rule_name"],
            "severity": r["severity"],
            "fields": r["fields"],
        }
        for r in rules
    ]

"""
SchemaGuard Rule Registry

Provides rule registration, lookup, and execution for domain-specific
semantic validation rules.
"""

from typing import Callable, TypedDict


class RuleResult(TypedDict):
    rule_id: str
    rule_name: str
    passed: bool
    severity: str       # "critical" | "warning" | "info"
    fields: list[str]
    message: str


# Type alias for rule functions
RuleFunction = Callable[[dict], RuleResult]


class RuleRegistry:
    """
    Registry for semantic validation rules.

    Rules are registered per domain. At validation time, all rules for
    a given domain are executed against the record.
    """

    def __init__(self):
        self._rules: dict[str, list[dict]] = {}

    def register(
        self,
        domain: str,
        rule_id: str,
        rule_name: str,
        severity: str,
        fields: list[str],
        fn: RuleFunction,
    ) -> None:
        """Register a rule function for a domain."""
        if domain not in self._rules:
            self._rules[domain] = []
        self._rules[domain].append({
            "rule_id": rule_id,
            "rule_name": rule_name,
            "severity": severity,
            "fields": fields,
            "fn": fn,
        })

    def get_rules(self, domain: str) -> list[dict]:
        """Return all registered rules for a domain."""
        return self._rules.get(domain, [])

    def list_domains(self) -> list[str]:
        """Return all domains with registered rules."""
        return list(self._rules.keys())

    def run_all(self, domain: str, record: dict) -> list[RuleResult]:
        """Execute all rules for a domain against a record."""
        results = []
        for rule in self.get_rules(domain):
            try:
                result = rule["fn"](record)
                results.append(result)
            except Exception as e:
                results.append(RuleResult(
                    rule_id=rule["rule_id"],
                    rule_name=rule["rule_name"],
                    passed=False,
                    severity=rule["severity"],
                    fields=rule["fields"],
                    message=f"Rule execution error: {str(e)}",
                ))
        return results


# Global registry instance
registry = RuleRegistry()


def register_rule(
    domain: str,
    rule_id: str,
    rule_name: str,
    severity: str = "critical",
    fields: list[str] | None = None,
):
    """
    Decorator to register a semantic validation rule.

    Usage:
        @register_rule(
            domain="healthcare_intake",
            rule_id="HC-003",
            rule_name="discharge_after_admission",
            severity="critical",
            fields=["admission_date", "discharge_date"],
        )
        def check_discharge_after_admission(record: dict) -> RuleResult:
            ...
    """
    def decorator(fn: RuleFunction) -> RuleFunction:
        registry.register(
            domain=domain,
            rule_id=rule_id,
            rule_name=rule_name,
            severity=severity,
            fields=fields or [],
            fn=fn,
        )
        return fn
    return decorator

"""
SchemaGuard — Rules Package

Import this package to register all domain rules with the global registry.
"""

from rules.rule_registry import registry, register_rule, RuleResult

# Import rule modules to trigger @register_rule decorators
import rules.healthcare_rules  # noqa: F401
import rules.finance_rules     # noqa: F401

__all__ = ["registry", "register_rule", "RuleResult"]

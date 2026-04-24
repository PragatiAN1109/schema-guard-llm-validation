"""
SchemaGuard — Correction Suggestions Package

Maps each violated rule to field-level corrections the user can apply
to bring a record into compliance.
"""
from suggestions.engine import suggest_fixes, SuggestionResult

__all__ = ["suggest_fixes", "SuggestionResult"]

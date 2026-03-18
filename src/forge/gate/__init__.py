"""FORGE Gate Engine — trust system for review routing.

The Gate Engine is a trust system, not a review scheduler. It determines
review intensity based on worker trust and task blast radius.

Phase 1: Single reviewer + escalation on fail, shadow mode.
Phase 2+: Trust × blast-radius matrix, auto-merge, full board review.

See: FORGE_ARCHITECTURE_v0.2.md §5
"""

from forge.gate.engine import (
    DifficultyClass,
    GateEngine,
    ReviewerRole,
    Verdict,
    VerdictOutcome,
    VerdictIssue,
)

__all__ = [
    "DifficultyClass",
    "GateEngine",
    "ReviewerRole",
    "Verdict",
    "VerdictOutcome",
    "VerdictIssue",
]

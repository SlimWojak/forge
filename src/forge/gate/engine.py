"""FORGE Gate Engine — trust-based review routing.

The Gate Engine is a trust system that determines review intensity
based on worker trust and task blast radius.

Phase 1 flow (§5.3):
  1. Worker completes task
  2. Mechanical checks run (no frontier call on failure)
  3. Oracle generated
  4. Single frontier reviewer receives Core Oracle
  5. PASS → propose commit (shadow mode)
  6. FAIL → structured TODO to worker
  7. FAIL ×2 → escalate to second reviewer
  8. FAIL ×3 → recovery mode

See: FORGE_ARCHITECTURE_v0.2.md §5
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DifficultyClass(Enum):
    """Task difficulty classification.

    Every task is classified before execution begins.
    Phase 1: planner model classifies. Human can override.
    Phase 2+: trained classifier using historical data.

    See: §5.2 Difficulty Classifier
    """

    MECHANICAL = "mechanical"
    LOCAL_REASONING = "local-reasoning"
    ARCHITECTURAL = "architectural"
    UNCERTAIN = "uncertain"


class VerdictOutcome(Enum):
    """Possible outcomes of a gate review."""

    PASS = "PASS"
    FAIL = "FAIL"


class ReviewerRole(Enum):
    """Role of a frontier reviewer in the gate process."""

    PRIMARY_REVIEWER = "primary_reviewer"
    ESCALATION_REVIEWER = "escalation_reviewer"
    CHAIRMAN = "chairman"  # Phase 2+


class ErrorTaxonomyTag(Enum):
    """Error taxonomy tags assigned by frontier reviewers.

    Every failure is tagged with one or more categories.
    Used for boundary measurement and skill crystallization.

    See: §7.4 Error Taxonomy
    """

    TOOL_MISUSE = "tool-misuse"
    NAVIGATION_FAILURE = "navigation-failure"
    INCORRECT_LOGIC = "incorrect-logic"
    MISSING_TESTS = "missing-tests"
    ARCHITECTURAL_DRIFT = "architectural-drift"
    CONTEXT_CONFUSION = "context-confusion"
    FLAKY_VALIDATION = "flaky-validation"


# ---------------------------------------------------------------------------
# Dataclasses matching Verdict schema (§5.6)
# ---------------------------------------------------------------------------


@dataclass
class VerdictIssue:
    """A single issue identified by a reviewer.

    Each issue includes: WHAT is wrong, WHY it matters, HOW to fix it,
    and acceptance criteria for the fix.
    """

    id: str
    file: str
    line_range: list[int]  # [start, end]
    severity: str  # "blocking" | "warning" | "suggestion"
    category: str  # ErrorTaxonomyTag value
    what: str
    why: str
    fix: str
    acceptance_criteria: str


@dataclass
class ReviewerInfo:
    """Information about the reviewer that produced a verdict."""

    model: str
    provider: str  # "anthropic" | "openai" | "xai"
    role: str  # ReviewerRole value


@dataclass
class Verdict:
    """A frontier reviewer's verdict on a task.

    Schema: forge-verdict-v0.2
    See: §5.6 Verdict Schema
    """

    verdict_id: str
    oracle_id: str
    task_id: str
    timestamp: str
    reviewer: ReviewerInfo
    verdict: VerdictOutcome
    error_taxonomy_tags: list[str] = field(default_factory=list)
    summary: str = ""
    issues: list[VerdictIssue] = field(default_factory=list)
    annexes_pulled: list[str] = field(default_factory=list)
    oracle_sections_referenced: list[str] = field(default_factory=list)
    tokens_consumed: dict[str, int] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict matching the normative schema."""
        # TODO: Implement full serialization matching §5.6 schema
        raise NotImplementedError("Verdict.to_json not yet implemented")

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Verdict:
        """Deserialize from JSON dict."""
        # TODO: Implement deserialization with validation
        raise NotImplementedError("Verdict.from_json not yet implemented")


@dataclass
class DifficultyClassification:
    """Result of the difficulty classifier.

    See: §5.2 Classifier interface
    """

    difficulty_class: DifficultyClass
    confidence: float
    rationale: str


# ---------------------------------------------------------------------------
# Gate Engine
# ---------------------------------------------------------------------------


class GateEngine:
    """Trust-based review routing engine.

    Phase 1: single reviewer + escalation. Shadow mode always on.
    Phase 2+: Trust × blast-radius matrix, auto-merge, full board.

    Usage::

        engine = GateEngine(config=gate_config)
        verdict = engine.send_to_reviewer(oracle=core_oracle)
        if verdict.verdict == VerdictOutcome.PASS:
            engine.propose_commit(task_id)
        else:
            engine.return_todo_to_worker(verdict)

    See: FORGE_ARCHITECTURE_v0.2.md §5
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the Gate Engine with gate configuration.

        Args:
            config: Gate configuration from .forge/config.yaml gate section.
                    See §13.1 for schema.
        """
        self._config = config or {}
        self._max_iterations = self._config.get("max_iterations", 3)
        self._recovery_threshold = self._config.get("recovery_threshold", 3)
        self._shadow_mode = self._config.get("shadow_mode", True)

    def difficulty_classifier(
        self,
        task_description: str,
        file_paths_hint: list[str] | None = None,
        codemap: dict[str, Any] | None = None,
    ) -> DifficultyClassification:
        """Classify task difficulty before execution.

        Phase 1: Uses planner model to classify.
        Human can override via `forge task --difficulty`.

        Args:
            task_description: Description of the task.
            file_paths_hint: Optional list of files likely to be changed.
            codemap: Optional codemap of the affected area.

        Returns:
            DifficultyClassification with class, confidence, rationale.

        See: §5.2 Difficulty Classifier

        TODO: Implement planner-based classification (§5.2).
        TODO: Support manual override from CLI.
        TODO: Store classification in task state.
        """
        raise NotImplementedError(
            "difficulty_classifier not yet implemented — see §5.2"
        )

    def send_to_reviewer(
        self,
        oracle: Any,  # CoreOracle — avoids circular import
        iteration: int = 1,
    ) -> Verdict:
        """Send Oracle to frontier reviewer and get verdict.

        Phase 1 flow (§5.3):
        - iteration 1-2: primary reviewer
        - iteration 2 with FAIL: escalate to second reviewer
        - iteration 3+: recovery mode

        Args:
            oracle: The Core Oracle to send for review.
            iteration: Current iteration count for this task.

        Returns:
            Verdict from the frontier reviewer.

        TODO: Implement frontier API call with Oracle payload (§5.3).
        TODO: Wire reviewer model from config (§13.1).
        TODO: Handle annex requests from reviewer (§4.2 Tier 2).
        TODO: Store verdict in .forge/verdicts/.
        TODO: Record in observability pipeline.
        """
        raise NotImplementedError("send_to_reviewer not yet implemented — see §5.3")

    def should_escalate(self, iteration: int) -> bool:
        """Check if review should escalate to a second reviewer.

        Escalation occurs on the second consecutive FAIL (§5.3).

        Args:
            iteration: Current iteration number.

        Returns:
            True if a second reviewer should be consulted.
        """
        return iteration >= 2

    def should_enter_recovery(self, iteration: int) -> bool:
        """Check if the task should enter recovery mode.

        Recovery mode activates after N consecutive failures (§3.3).

        Args:
            iteration: Current iteration number.

        Returns:
            True if recovery mode should be activated.
        """
        return iteration >= self._recovery_threshold

    def propose_commit(self, task_id: str, verdict: Verdict) -> dict[str, Any]:
        """Propose a commit for human approval (shadow mode).

        In shadow mode, FORGE proposes commits but humans are the
        final merger. The proposal includes full context: Oracle,
        verdict, and diff.

        Args:
            task_id: The task that passed review.
            verdict: The PASS verdict from the reviewer.

        Returns:
            Proposal dict with task_id, oracle_id, verdict_id.

        See: §5.5 Shadow Mode

        TODO: Implement shadow-mode proposal (§5.5).
        TODO: Log shadow_event to shadow-log.jsonl.
        TODO: Notify human via CLI status.
        """
        raise NotImplementedError("propose_commit not yet implemented — see §5.5")

    def record_human_decision(
        self,
        task_id: str,
        oracle_id: str,
        decision: str,
        feedback: str | None = None,
    ) -> None:
        """Record a human merge/reject decision as a training signal.

        Every human decision in shadow mode is logged for future
        training data and boundary measurement.

        Args:
            task_id: The task being decided on.
            oracle_id: The Oracle that was reviewed.
            decision: "approved" or "rejected".
            feedback: Optional human feedback text.

        See: §5.5 Shadow mode data capture

        TODO: Append to .forge/shadow-log.jsonl (§5.5).
        TODO: Update shadow_log table in DuckDB.
        """
        raise NotImplementedError(
            "record_human_decision not yet implemented — see §5.5"
        )

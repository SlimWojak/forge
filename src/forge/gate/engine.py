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

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

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
        return {
            "$schema": "forge-verdict-v0.2",
            "verdict_id": self.verdict_id,
            "oracle_id": self.oracle_id,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "reviewer": asdict(self.reviewer),
            "verdict": self.verdict.value,
            "error_taxonomy_tags": self.error_taxonomy_tags,
            "summary": self.summary,
            "issues": [asdict(i) for i in self.issues],
            "annexes_pulled": self.annexes_pulled,
            "oracle_sections_referenced": self.oracle_sections_referenced,
            "tokens_consumed": self.tokens_consumed,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Verdict:
        """Deserialize from JSON dict."""
        issues = [
            VerdictIssue(**i) for i in data.get("issues", [])
        ]
        reviewer = ReviewerInfo(**data.get("reviewer", {
            "model": "unknown", "provider": "unknown", "role": "unknown",
        }))
        return cls(
            verdict_id=data.get("verdict_id", ""),
            oracle_id=data.get("oracle_id", ""),
            task_id=data.get("task_id", ""),
            timestamp=data.get("timestamp", ""),
            reviewer=reviewer,
            verdict=VerdictOutcome(data.get("verdict", "FAIL")),
            error_taxonomy_tags=data.get("error_taxonomy_tags", []),
            summary=data.get("summary", ""),
            issues=issues,
            annexes_pulled=data.get("annexes_pulled", []),
            oracle_sections_referenced=data.get(
                "oracle_sections_referenced", []
            ),
            tokens_consumed=data.get("tokens_consumed", {}),
        )


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


class ReviewerModel(Protocol):
    """Protocol for the frontier reviewer model backend.

    Allows mocking in tests without requiring real API endpoints.
    """

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Send messages and return a completion response."""
        ...


REVIEWER_SYSTEM_PROMPT = """\
You are a FORGE code reviewer. You receive an Oracle snapshot describing \
a task completion and must produce a structured verdict.

Your verdict MUST be valid JSON with this exact structure:
{
  "verdict": "PASS" or "FAIL",
  "error_taxonomy_tags": [],
  "summary": "Brief explanation",
  "issues": [
    {
      "id": "issue-001",
      "file": "path/to/file",
      "line_range": [start, end],
      "severity": "blocking" or "warning" or "suggestion",
      "category": "one of: tool-misuse, navigation-failure, \
incorrect-logic, missing-tests, architectural-drift, \
context-confusion, flaky-validation",
      "what": "What is wrong",
      "why": "Why it matters",
      "fix": "How to fix it",
      "acceptance_criteria": "How to verify the fix"
    }
  ]
}

Rules:
- PASS if the implementation is correct, tested, and architecturally sound
- FAIL if there are blocking issues (include structured TODOs)
- Every FAIL must have at least one issue with severity "blocking"
- Be specific: reference files, line ranges, and concrete fixes
- Tag every issue with an error_taxonomy_tag
"""


def _parse_verdict_json(
    text: str,
    oracle_id: str,
    task_id: str,
    reviewer_info: ReviewerInfo,
) -> Verdict:
    """Parse a verdict JSON from reviewer output text."""
    # Try to extract JSON from the response
    json_match = None
    # Look for JSON block in markdown code fence
    import re

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        json_match = fence_match.group(1)
    else:
        # Try to find bare JSON object
        brace_match = re.search(r"\{.*\"verdict\".*\}", text, re.DOTALL)
        if brace_match:
            json_match = brace_match.group()

    if json_match is None:
        # Heuristic: if the text contains "PASS", treat as PASS
        outcome = VerdictOutcome.PASS if "PASS" in text.upper() else VerdictOutcome.FAIL
        return Verdict(
            verdict_id=f"verdict-{uuid.uuid4().hex[:8]}",
            oracle_id=oracle_id,
            task_id=task_id,
            timestamp=datetime.now(UTC).isoformat(),
            reviewer=reviewer_info,
            verdict=outcome,
            summary=text[:500],
        )

    try:
        data = json.loads(json_match)
    except json.JSONDecodeError:
        return Verdict(
            verdict_id=f"verdict-{uuid.uuid4().hex[:8]}",
            oracle_id=oracle_id,
            task_id=task_id,
            timestamp=datetime.now(UTC).isoformat(),
            reviewer=reviewer_info,
            verdict=VerdictOutcome.FAIL,
            summary=f"Failed to parse reviewer JSON: {text[:200]}",
        )

    outcome = VerdictOutcome.PASS if data.get("verdict") == "PASS" else VerdictOutcome.FAIL

    issues: list[VerdictIssue] = []
    for i_data in data.get("issues", []):
        issues.append(VerdictIssue(
            id=i_data.get("id", f"issue-{len(issues)+1:03d}"),
            file=i_data.get("file", ""),
            line_range=i_data.get("line_range", [0, 0]),
            severity=i_data.get("severity", "blocking"),
            category=i_data.get("category", ""),
            what=i_data.get("what", ""),
            why=i_data.get("why", ""),
            fix=i_data.get("fix", ""),
            acceptance_criteria=i_data.get("acceptance_criteria", ""),
        ))

    return Verdict(
        verdict_id=f"verdict-{uuid.uuid4().hex[:8]}",
        oracle_id=oracle_id,
        task_id=task_id,
        timestamp=datetime.now(UTC).isoformat(),
        reviewer=reviewer_info,
        verdict=outcome,
        error_taxonomy_tags=data.get("error_taxonomy_tags", []),
        summary=data.get("summary", ""),
        issues=issues,
    )


class GateEngine:
    """Trust-based review routing engine.

    Phase 1: single reviewer + escalation. Shadow mode always on.

    See: FORGE_ARCHITECTURE_v0.2.md §5
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        project_root: Path | None = None,
        reviewer: ReviewerModel | None = None,
        escalation_reviewer: ReviewerModel | None = None,
    ) -> None:
        self._config = config or {}
        self._project_root = project_root or Path(".")
        self._max_iterations = self._config.get("max_iterations", 3)
        self._recovery_threshold = self._config.get("recovery_threshold", 3)
        self._shadow_mode = self._config.get("shadow_mode", True)
        self._reviewer = reviewer
        self._escalation_reviewer = escalation_reviewer

        self._verdicts_dir = self._project_root / ".forge" / "verdicts"
        self._verdicts_dir.mkdir(parents=True, exist_ok=True)
        self._shadow_log = self._project_root / ".forge" / "shadow-log.jsonl"

    def difficulty_classifier(
        self,
        task_description: str,
        file_paths_hint: list[str] | None = None,
    ) -> DifficultyClassification:
        """Classify task difficulty. Phase 1: keyword heuristic.

        See: §5.2
        """
        desc_lower = task_description.lower()

        if any(w in desc_lower for w in [
            "lint", "format", "type annotation", "dep bump", "config",
            "rename", "typo",
        ]):
            return DifficultyClassification(
                difficulty_class=DifficultyClass.MECHANICAL,
                confidence=0.7,
                rationale="Task description matches mechanical keywords",
            )
        elif any(w in desc_lower for w in [
            "refactor", "migrate", "redesign", "cross-module", "schema",
            "architecture",
        ]):
            return DifficultyClassification(
                difficulty_class=DifficultyClass.ARCHITECTURAL,
                confidence=0.6,
                rationale="Task description suggests architectural changes",
            )
        elif any(w in desc_lower for w in [
            "implement", "add", "create", "build", "fix", "test", "write",
        ]):
            return DifficultyClassification(
                difficulty_class=DifficultyClass.LOCAL_REASONING,
                confidence=0.65,
                rationale="Task description suggests focused implementation",
            )
        else:
            return DifficultyClassification(
                difficulty_class=DifficultyClass.UNCERTAIN,
                confidence=0.3,
                rationale="Could not classify from description alone",
            )

    def send_to_reviewer(
        self,
        oracle: Any,
        iteration: int = 1,
        task_id: str = "",
    ) -> Verdict:
        """Send Oracle to frontier reviewer and get verdict.

        Phase 1 flow (§5.3):
        - iteration 1: primary reviewer
        - iteration 2: escalate to second reviewer
        - iteration 3+: recovery mode territory

        See: §5.3
        """
        if self._reviewer is None:
            raise RuntimeError(
                "No reviewer model configured. Set reviewer in GateEngine init "
                "or configure models.frontier.reviewer in .forge/config.yaml"
            )

        # Determine which reviewer to use
        use_escalation = self.should_escalate(iteration) and self._escalation_reviewer
        model = self._escalation_reviewer if use_escalation else self._reviewer
        role = "escalation_reviewer" if use_escalation else "primary_reviewer"

        # Serialize oracle
        oracle_json = oracle.to_json() if hasattr(oracle, "to_json") else oracle
        oracle_id = oracle_json.get("oracle_id", "") if isinstance(oracle_json, dict) else ""

        reviewer_info = ReviewerInfo(
            model=self._config.get("default_reviewer", "unknown"),
            provider=self._config.get("provider", "unknown"),
            role=role,
        )

        messages = [
            {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Review this Oracle snapshot and produce a verdict:\n\n"
                    f"```json\n{json.dumps(oracle_json, indent=2)}\n```"
                ),
            },
        ]

        try:
            response = model.chat_completion(messages=messages)
        except Exception as e:
            # API error — return a FAIL verdict indicating the error
            return Verdict(
                verdict_id=f"verdict-{uuid.uuid4().hex[:8]}",
                oracle_id=oracle_id,
                task_id=task_id,
                timestamp=datetime.now(UTC).isoformat(),
                reviewer=reviewer_info,
                verdict=VerdictOutcome.FAIL,
                summary=f"Reviewer API error: {e}",
                error_taxonomy_tags=["flaky-validation"],
            )

        # Parse the response
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        verdict = _parse_verdict_json(content, oracle_id, task_id, reviewer_info)

        # Persist verdict
        verdict_path = self._verdicts_dir / f"{verdict.verdict_id}.json"
        verdict_path.write_text(json.dumps(verdict.to_json(), indent=2))

        return verdict

    def should_escalate(self, iteration: int) -> bool:
        """Escalation occurs on the second consecutive FAIL (§5.3)."""
        return iteration >= 2

    def should_enter_recovery(self, iteration: int) -> bool:
        """Recovery mode activates after N consecutive failures (§3.3)."""
        return iteration >= self._recovery_threshold

    def propose_commit(
        self, task_id: str, verdict: Verdict
    ) -> dict[str, Any]:
        """Propose a commit for human approval (shadow mode).

        See: §5.5
        """
        proposal = {
            "task_id": task_id,
            "oracle_id": verdict.oracle_id,
            "verdict_id": verdict.verdict_id,
            "verdict": verdict.verdict.value,
            "summary": verdict.summary,
            "shadow_mode": self._shadow_mode,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Log shadow event
        shadow_event = {
            "shadow_event": {
                "task_id": task_id,
                "oracle_id": verdict.oracle_id,
                "gate_verdict": verdict.verdict.value,
                "human_decision": "pending",
                "human_feedback": None,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        }
        with open(self._shadow_log, "a") as f:
            f.write(json.dumps(shadow_event) + "\n")

        return proposal

    def record_human_decision(
        self,
        task_id: str,
        oracle_id: str,
        decision: str,
        feedback: str | None = None,
    ) -> None:
        """Record a human merge/reject decision.

        See: §5.5
        """
        event = {
            "shadow_event": {
                "task_id": task_id,
                "oracle_id": oracle_id,
                "gate_verdict": "PASS",
                "human_decision": decision,
                "human_feedback": feedback,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        }
        with open(self._shadow_log, "a") as f:
            f.write(json.dumps(event) + "\n")

    def extract_todos_from_verdict(self, verdict: Verdict) -> list[dict[str, Any]]:
        """Extract structured TODOs from a FAIL verdict for the worker."""
        todos: list[dict[str, Any]] = []
        for issue in verdict.issues:
            if issue.severity == "blocking":
                todos.append({
                    "file": issue.file,
                    "line_range": issue.line_range,
                    "what": issue.what,
                    "fix": issue.fix,
                    "acceptance_criteria": issue.acceptance_criteria,
                })
        return todos

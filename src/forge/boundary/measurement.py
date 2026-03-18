"""FORGE Boundary Measurement — data capture and analysis.

Every completed task produces a boundary record (§7.2) that is:
1. Appended to .forge/boundary-data.jsonl (append-only)
2. Ingested into DuckDB for querying

The `forge boundary` command queries this data to produce the
frontier/local split report (§7.3).

See: FORGE_ARCHITECTURE_v0.2.md §7
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Error Taxonomy (§7.4)
# ---------------------------------------------------------------------------


class ErrorTaxonomy(Enum):
    """Error taxonomy tags assigned by frontier reviewers.

    Every failure is tagged with one or more categories.
    Tags are stored on each verdict and boundary record.
    Queryable via DuckDB.

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
# Boundary Record (§7.2)
# ---------------------------------------------------------------------------


@dataclass
class ClassificationInfo:
    """How the task was classified."""

    difficulty_class: str
    classified_by: str  # "planner" | "human"
    classification_confidence: float


@dataclass
class WorkerInfo:
    """Worker identity in a boundary record."""

    model: str
    lora_version: str | None = None
    serving_config: str = ""


@dataclass
class OutcomeInfo:
    """Task outcome for boundary measurement."""

    first_pass_success: bool
    total_iterations: int
    final_verdict: str  # "PASS" | "FAIL"
    error_taxonomy_tags: list[str] = field(default_factory=list)
    frontier_intervention_type: str = ""
    recovery_mode_activated: bool = False


@dataclass
class CostInfo:
    """Cost tracking for a boundary record."""

    local_tokens: int = 0
    frontier_tokens_in: int = 0
    frontier_tokens_out: int = 0
    frontier_cost_usd: float = 0.0
    wall_clock_seconds: int = 0


@dataclass
class OracleUtilization:
    """How the Oracle was used during review."""

    core_sections_referenced: list[str] = field(default_factory=list)
    annexes_pulled: list[str] = field(default_factory=list)


@dataclass
class BoundaryRecord:
    """A single boundary measurement data point.

    Produced for every completed task. Stored as append-only JSONL
    in .forge/boundary-data.jsonl and ingested into DuckDB.

    Schema: forge-boundary-record-v0.2
    See: §7.2 Data Capture
    """

    task_id: str
    mission_id: str
    mission_mode: str  # "delivery" | "research"
    timestamp: str

    classification: ClassificationInfo | None = None
    worker: WorkerInfo | None = None
    outcome: OutcomeInfo | None = None
    cost: CostInfo | None = None
    oracle_utilization: OracleUtilization | None = None

    def to_json(self) -> dict[str, Any]:
        """Serialize to JSON for JSONL storage and DuckDB ingestion."""
        # TODO: Implement full serialization matching §7.2 schema
        raise NotImplementedError("BoundaryRecord.to_json not yet implemented")

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> BoundaryRecord:
        """Deserialize from JSON."""
        # TODO: Implement deserialization
        raise NotImplementedError("BoundaryRecord.from_json not yet implemented")


# ---------------------------------------------------------------------------
# Boundary Tracker
# ---------------------------------------------------------------------------


class BoundaryTracker:
    """Tracks and analyzes boundary measurement data.

    Records boundary data for every task and provides query methods
    for the `forge boundary` and `forge taxonomy` commands.

    Usage::

        tracker = BoundaryTracker(project_root=Path("."))
        tracker.record(boundary_record)

        report = tracker.generate_report(period="7d")
        taxonomy = tracker.generate_taxonomy(period="30d")

    See: FORGE_ARCHITECTURE_v0.2.md §7
    """

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root
        self._data_path = project_root / ".forge" / "boundary-data.jsonl"

    def record(self, record: BoundaryRecord) -> None:
        """Append a boundary record to storage.

        Writes to both:
        1. .forge/boundary-data.jsonl (append-only JSONL)
        2. DuckDB boundary_records table

        Args:
            record: The boundary record to store.

        TODO: Implement JSONL append (§7.2).
        TODO: Implement DuckDB INSERT via ForgeTracer.
        """
        raise NotImplementedError("record not yet implemented — see §7.2")

    def generate_report(
        self,
        period: str = "7d",
        by_type: bool = False,
        by_worker: bool = False,
    ) -> str:
        """Generate the `forge boundary` report.

        Produces the output format shown in §7.3:
        - Local first-pass success rate
        - Frontier correction rate
        - Breakdown by task type
        - Breakdown by worker
        - Boundary movement trends
        - Top frontier corrections
        - Cost summary

        Args:
            period: Time window ("7d", "30d", "all").
            by_type: Include difficulty class breakdown.
            by_worker: Include worker identity breakdown.

        Returns:
            Formatted report string.

        TODO: Implement DuckDB query and report generation (§7.3).
        """
        raise NotImplementedError("generate_report not yet implemented — see §7.3")

    def generate_taxonomy(self, period: str = "30d") -> str:
        """Generate the `forge taxonomy` report.

        Produces the error taxonomy distribution output shown in §7.4:
        - Tag distribution with percentages and bar charts
        - Trend comparison vs previous period

        Args:
            period: Time window ("7d", "30d", "all").

        Returns:
            Formatted taxonomy report string.

        TODO: Implement DuckDB query and taxonomy report (§7.4).
        """
        raise NotImplementedError("generate_taxonomy not yet implemented — see §7.4")

    def get_first_pass_rate(
        self,
        period: str = "7d",
        difficulty_class: str | None = None,
    ) -> float:
        """Get the first-pass success rate for the period.

        Args:
            period: Time window.
            difficulty_class: Optional filter by difficulty.

        Returns:
            First-pass success rate as a float (0.0 to 1.0).

        TODO: Implement DuckDB aggregation query.
        """
        raise NotImplementedError("get_first_pass_rate not yet implemented")

    def get_boundary_movement(
        self,
        period: str = "30d",
    ) -> dict[str, dict[str, float]]:
        """Get boundary movement trends over time.

        Returns per-difficulty-class rates at start and end of period.

        TODO: Implement trend computation (§7.3).
        """
        raise NotImplementedError("get_boundary_movement not yet implemented")

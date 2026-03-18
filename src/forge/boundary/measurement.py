"""FORGE Boundary Measurement — data capture and analysis.

Every completed task produces a boundary record (§7.2) that is:
1. Appended to .forge/boundary-data.jsonl (append-only)
2. Ingested into DuckDB for querying

The `forge boundary` command queries this data to produce the
frontier/local split report (§7.3).

See: FORGE_ARCHITECTURE_v0.2.md §7
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
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
        result: dict[str, Any] = {
            "task_id": self.task_id,
            "mission_id": self.mission_id,
            "mission_mode": self.mission_mode,
            "timestamp": self.timestamp,
        }
        if self.classification:
            result["classification"] = asdict(self.classification)
        if self.worker:
            result["worker"] = asdict(self.worker)
        if self.outcome:
            result["outcome"] = asdict(self.outcome)
        if self.cost:
            result["cost"] = asdict(self.cost)
        return result

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> BoundaryRecord:
        """Deserialize from JSON."""
        rec = cls(
            task_id=data["task_id"],
            mission_id=data["mission_id"],
            mission_mode=data["mission_mode"],
            timestamp=data["timestamp"],
        )
        if "classification" in data:
            rec.classification = ClassificationInfo(**data["classification"])
        if "worker" in data:
            rec.worker = WorkerInfo(**data["worker"])
        if "outcome" in data:
            rec.outcome = OutcomeInfo(**data["outcome"])
        if "cost" in data:
            rec.cost = CostInfo(**data["cost"])
        return rec


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
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: list[BoundaryRecord] = []
        self._load_records()

    def _load_records(self) -> None:
        if self._data_path.exists():
            for line in self._data_path.read_text().strip().splitlines():
                if line.strip():
                    self._records.append(BoundaryRecord.from_json(json.loads(line)))

    def record(self, rec: BoundaryRecord) -> None:
        """Append a boundary record to JSONL storage."""
        self._records.append(rec)
        with open(self._data_path, "a") as f:
            f.write(json.dumps(rec.to_json()) + "\n")

    def generate_report(
        self,
        period: str = "7d",
        by_type: bool = False,
        by_worker: bool = False,
    ) -> str:
        """Generate the forge boundary report. See §7.3."""
        records = self._records
        if not records:
            return "No boundary data recorded yet."

        total = len(records)
        first_pass = sum(
            1 for r in records
            if r.outcome and r.outcome.first_pass_success
        )
        rate = first_pass / total if total > 0 else 0.0

        lines = [
            "FORGE Boundary Report",
            f"  Period: {period}",
            f"  Total tasks: {total}",
            f"  First-pass success: {first_pass}/{total} ({rate:.0%})",
            f"  Frontier correction: {total - first_pass}/{total}",
        ]

        if by_type:
            by_diff: dict[str, list[BoundaryRecord]] = {}
            for r in records:
                dc = r.classification.difficulty_class if r.classification else "unknown"
                by_diff.setdefault(dc, []).append(r)
            lines.append("")
            lines.append("  By difficulty class:")
            for dc, recs in sorted(by_diff.items()):
                fp = sum(1 for r in recs if r.outcome and r.outcome.first_pass_success)
                lines.append(f"    {dc}: {fp}/{len(recs)} ({fp / len(recs):.0%})")

        total_cost = sum(
            r.cost.frontier_cost_usd for r in records if r.cost
        )
        lines.append(f"  Total frontier cost: ${total_cost:.4f}")

        return "\n".join(lines)

    def generate_taxonomy(self, period: str = "30d") -> str:
        """Generate error taxonomy distribution. See §7.4."""
        tag_counts: dict[str, int] = {}
        for r in self._records:
            if r.outcome:
                for tag in r.outcome.error_taxonomy_tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        if not tag_counts:
            return "No error taxonomy data recorded yet."

        total = sum(tag_counts.values())
        lines = ["FORGE Error Taxonomy", f"  Total failure tags: {total}", ""]
        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100
            bar = "#" * int(pct / 5)
            lines.append(f"  {tag:<25} {count:>3} ({pct:>5.1f}%) {bar}")

        return "\n".join(lines)

    def get_first_pass_rate(
        self,
        period: str = "7d",
        difficulty_class: str | None = None,
    ) -> float:
        records = self._records
        if difficulty_class:
            records = [
                r for r in records
                if r.classification and r.classification.difficulty_class == difficulty_class
            ]
        if not records:
            return 0.0
        passed = sum(
            1 for r in records if r.outcome and r.outcome.first_pass_success
        )
        return passed / len(records)

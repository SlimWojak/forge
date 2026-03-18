"""FORGE Oracle Generator — two-tier Oracle pipeline.

The Oracle Generator produces structured snapshots that mediate between
local workers and frontier reviewers. The pipeline is mechanical (no LLM
required for core generation) and uses tree-sitter for code analysis.

Pipeline steps (§4.4):
  1. git diff → compute diff against main branch
  2. tree-sitter parse → extract signatures, deps, call graph
  3. Dependency analysis → follow imports (1 hop)
  4. Mechanical checks → lint, typecheck, test suite, build
  5. Desloppify mechanical scan → quality metrics on changed files
  6. Worker self-assessment → extract from worker's final message
  7. Assemble Core Oracle → combine into Tier 1 JSON
  8. Stage annexes → write Tier 2 files to disk

See: FORGE_ARCHITECTURE_v0.2.md §4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AnnexType(Enum):
    """Types of Tier 2 expandable annexes.

    Reviewers pull these on demand. Not auto-included in Core Oracle.

    See: §4.2 Tier 2 Annexes table
    """

    FULL_PATCH = "full_patch"
    FILE = "file"  # file:<path>
    TEST_OUTPUT = "test_output"
    PRIOR_VERDICTS = "prior_verdicts"
    LINT_DETAILS = "lint_details"


# ---------------------------------------------------------------------------
# Dataclasses matching the Oracle JSON schema (§4.2)
# ---------------------------------------------------------------------------


@dataclass
class TaskContext:
    """Context about the task being reviewed.

    Embedded in the Core Oracle to give reviewers situational awareness.
    """

    mission: str
    milestone: str
    milestone_description: str
    task_id: str
    task_description: str
    difficulty_class: str
    mission_mode: str  # "delivery" | "research"
    feature_list_progress: str
    milestone_progress: str
    iteration: int
    total_iterations_this_task: int


@dataclass
class WorkerIdentity:
    """First-class tracking of the model that produced the output.

    Includes historical success rates for boundary measurement context.
    """

    model: str
    lora_version: str | None
    serving_config: str
    historical_success_rate: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiffSummary:
    """Summary of code changes in the diff.

    Captures file-level and function-level changes for the Core Oracle.
    """

    files_changed: int
    files_added: int
    files_deleted: int
    insertions: int
    deletions: int
    functions_added: list[str] = field(default_factory=list)
    functions_modified: list[str] = field(default_factory=list)
    functions_deleted: list[str] = field(default_factory=list)


@dataclass
class ChangedFile:
    """Tree-sitter analysis of a single changed file."""

    path: str
    language: str
    signatures: list[str] = field(default_factory=list)
    imports_added: list[str] = field(default_factory=list)
    exports_added: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass
class AffectedFile:
    """A file affected by changes (1-hop dependency)."""

    path: str
    change_summary: str


@dataclass
class Codemap:
    """Tree-sitter structural map of changed and affected files."""

    changed_files: list[ChangedFile] = field(default_factory=list)
    affected_files: list[AffectedFile] = field(default_factory=list)


@dataclass
class MechanicalCheckResult:
    """Result of a single mechanical check (lint, typecheck, tests, build)."""

    status: str  # "pass" | "fail"
    errors: int = 0
    warnings: int = 0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class MechanicalChecks:
    """Aggregated results of all mechanical checks."""

    lint: MechanicalCheckResult | None = None
    type_check: MechanicalCheckResult | None = None
    tests: MechanicalCheckResult | None = None
    build: MechanicalCheckResult | None = None
    desloppify_mechanical: dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityDelta:
    """Quality score change from the Desloppify mechanical scan."""

    desloppify_mechanical_score: int
    delta_from_previous: str
    new_issues: list[str] = field(default_factory=list)
    resolved_issues: list[str] = field(default_factory=list)


@dataclass
class WorkerSelfAssessment:
    """Structured self-assessment extracted from the worker's final message."""

    confidence: str  # "low" | "medium" | "high"
    concerns: list[str] = field(default_factory=list)
    decisions_made: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    tool_call_count: int = 0
    tokens_consumed: int = 0


@dataclass
class CoreOracle:
    """Tier 1 Core Oracle — the default payload sent to all reviewers.

    Target size: 2-4K tokens. Contains everything a reviewer needs
    to make a PASS/FAIL decision without pulling annexes.

    Schema: forge-oracle-v0.2
    See: §4.2 Tier 1 Core Oracle
    """

    oracle_version: str = "0.2"
    oracle_id: str = ""
    timestamp: str = ""

    task_context: TaskContext | None = None
    worker_identity: WorkerIdentity | None = None
    diff_summary: DiffSummary | None = None
    codemap: Codemap | None = None
    mechanical_checks: MechanicalChecks | None = None
    quality_delta: QualityDelta | None = None
    worker_self_assessment: WorkerSelfAssessment | None = None
    available_annexes: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict matching the normative schema."""
        # TODO: Implement full serialization matching §4.2 schema
        raise NotImplementedError("CoreOracle.to_json not yet implemented")

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> CoreOracle:
        """Deserialize from JSON dict."""
        # TODO: Implement deserialization with validation
        raise NotImplementedError("CoreOracle.from_json not yet implemented")


@dataclass
class OracleMetadata:
    """Metadata about Oracle generation: timing, token counts, etc.

    Stored alongside the Core Oracle in .forge/oracles/<id>/metadata.json.
    """

    oracle_id: str
    generation_started: str
    generation_completed: str
    generation_duration_ms: int
    treesitter_parse_ms: int
    diff_computation_ms: int
    mechanical_checks_ms: int
    total_token_estimate: int


# ---------------------------------------------------------------------------
# Oracle Generator
# ---------------------------------------------------------------------------


class OracleGenerator:
    """Generates Oracle snapshots from task state and worktree.

    The generator runs the full pipeline defined in §4.4:
    diff → tree-sitter parse → dependency analysis → mechanical checks
    → Desloppify scan → worker self-assessment → assemble → stage annexes.

    Usage::

        generator = OracleGenerator(project_root=Path("."))
        oracle = generator.build_oracle(
            task_id="task-001",
            worktree_path=Path(".forge-worktrees/task-001"),
            main_branch="main",
        )

    See: FORGE_ARCHITECTURE_v0.2.md §4
    """

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root
        self._oracle_dir = project_root / ".forge" / "oracles"

    def generate_diff(
        self,
        worktree_path: Path,
        main_branch: str = "main",
    ) -> DiffSummary:
        """Step 1: Compute git diff against main branch.

        Runs `git diff main..worktree` and parses the output into
        a structured DiffSummary with file and function-level changes.

        Args:
            worktree_path: Path to the task's git worktree.
            main_branch: Branch to diff against. Default "main".

        Returns:
            DiffSummary with change statistics.

        TODO: Implement git diff parsing (§4.4 step 1).
        TODO: Extract function-level changes from diff hunks.
        """
        raise NotImplementedError("generate_diff not yet implemented — see §4.4")

    def generate_codemap(
        self,
        changed_files: list[str],
        worktree_path: Path,
    ) -> Codemap:
        """Steps 2-3: Tree-sitter parse + dependency analysis.

        Parses changed files with tree-sitter to extract:
        - Function/class signatures
        - Import/export declarations
        - Call graph edges

        Then follows imports 1 hop to identify affected files.

        Args:
            changed_files: List of changed file paths from the diff.
            worktree_path: Path to the task's git worktree.

        Returns:
            Codemap with changed_files and affected_files analysis.

        TODO: Implement tree-sitter parsing pipeline (§4.4 steps 2-3).
        TODO: Support multiple languages via tree-sitter-languages.
        TODO: Implement 1-hop dependency following.
        """
        raise NotImplementedError("generate_codemap not yet implemented — see §4.4")

    def run_mechanical_checks(
        self,
        worktree_path: Path,
    ) -> MechanicalChecks:
        """Step 4: Run lint, typecheck, test suite, build.

        Executes all configured mechanical checks and captures
        structured results for the Oracle.

        Args:
            worktree_path: Path to the task's git worktree.

        Returns:
            MechanicalChecks with per-check results.

        TODO: Implement check runners (§4.4 step 4).
        TODO: Detect project's lint/typecheck/build tools automatically.
        """
        raise NotImplementedError("run_mechanical_checks not yet implemented — see §4.4")

    def get_quality_delta(
        self,
        worktree_path: Path,
        changed_files: list[str],
    ) -> QualityDelta:
        """Step 5: Desloppify mechanical scan on changed files.

        Runs the tree-sitter-based quality metrics (dead code, duplication,
        complexity, function length, nesting depth) and computes the
        score delta from the previous scan.

        Args:
            worktree_path: Path to the task's git worktree.
            changed_files: List of changed file paths.

        Returns:
            QualityDelta with score, delta, new/resolved issues.

        TODO: Implement Desloppify mechanical scan (§4.4 step 5, §6.3).
        """
        raise NotImplementedError("get_quality_delta not yet implemented — see §4.4")

    def prompt_worker_self_assessment(
        self,
        worker_final_message: str,
    ) -> WorkerSelfAssessment:
        """Step 6: Extract structured self-assessment from worker.

        Parses the worker's final message (which is required to include
        structured JSON self-assessment per the system prompt contract).

        Args:
            worker_final_message: The worker's final output message.

        Returns:
            WorkerSelfAssessment with confidence, concerns, decisions.

        TODO: Implement JSON extraction from worker message (§4.4 step 6).
        TODO: Handle cases where worker output is malformed.
        """
        raise NotImplementedError(
            "prompt_worker_self_assessment not yet implemented — see §4.4"
        )

    def build_oracle(
        self,
        task_id: str,
        worktree_path: Path,
        main_branch: str = "main",
        worker_final_message: str = "",
        task_context: TaskContext | None = None,
        worker_identity: WorkerIdentity | None = None,
    ) -> CoreOracle:
        """Execute the full Oracle generation pipeline (§4.4).

        Runs all 8 steps in sequence and produces the Core Oracle
        plus staged annexes. Writes output to .forge/oracles/<id>/.

        Args:
            task_id: The task being reviewed.
            worktree_path: Path to the task's git worktree.
            main_branch: Branch to diff against.
            worker_final_message: Worker's final output for self-assessment.
            task_context: Pre-built task context (from orchestrator).
            worker_identity: Pre-built worker identity (from orchestrator).

        Returns:
            CoreOracle with all sections populated.

        TODO: Wire together all pipeline steps (§4.4).
        TODO: Generate unique oracle_id.
        TODO: Write Core Oracle to .forge/oracles/<id>/core.json.
        TODO: Stage annexes to .forge/oracles/<id>/annexes/.
        TODO: Write metadata to .forge/oracles/<id>/metadata.json.
        TODO: Record generation event in observability pipeline.
        """
        raise NotImplementedError("build_oracle not yet implemented — see §4.4")

    def _stage_annexes(
        self,
        oracle_id: str,
        worktree_path: Path,
        diff_text: str,
        test_output: str,
        prior_verdicts: list[dict[str, Any]],
    ) -> list[str]:
        """Step 8: Stage Tier 2 annexes to disk.

        Writes full patch, file contents, test output, and prior verdicts
        to .forge/oracles/<oracle-id>/annexes/ for on-demand retrieval.

        Args:
            oracle_id: The Oracle ID for directory naming.
            worktree_path: Path to the task's git worktree.
            diff_text: Full unified diff text.
            test_output: Full test runner output.
            prior_verdicts: Previous verdicts on this task.

        Returns:
            List of available annex identifiers.

        TODO: Implement annex staging (§4.4 step 8, §4.3).
        """
        raise NotImplementedError("_stage_annexes not yet implemented — see §4.3")

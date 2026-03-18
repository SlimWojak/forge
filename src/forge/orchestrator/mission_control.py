"""FORGE Orchestrator — Mission Control state machine.

Mission Control manages the full task lifecycle:
  INIT → PLANNING → DIFFICULTY_CLASSIFIED → EXECUTING →
  MECHANICAL_CHECKS → ORACLE_GENERATED → UNDER_REVIEW →
  VERDICT → (PASS → PROPOSE_COMMIT → SHADOW_MERGE) or
            (FAIL → iterate) or (FAIL×3 → RECOVERY_MODE)

See: FORGE_ARCHITECTURE_v0.2.md §3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# State Machine
# ---------------------------------------------------------------------------


class TaskState(Enum):
    """Task lifecycle states matching the state machine in §1.3.

    State transitions:
      INIT → PLANNING → DIFFICULTY_CLASSIFIED → EXECUTING
      EXECUTING → MECHANICAL_CHECKS
      MECHANICAL_CHECKS → ORACLE_GENERATED (pass) or EXECUTING (fail)
      ORACLE_GENERATED → UNDER_REVIEW
      UNDER_REVIEW → VERDICT
      VERDICT → PROPOSE_COMMIT (pass) or EXECUTING (fail, iter < N)
      VERDICT → ESCALATE_REVIEWER (fail, iter == 2)
      VERDICT → RECOVERY_MODE (fail, iter >= 3)
      PROPOSE_COMMIT → SHADOW_MERGE → NEXT_TASK
      RECOVERY_MODE → REWRITE_TASK | SPLIT_TASK | ESCALATE_HUMAN | ABORT_TASK
      MILESTONE_BOUNDARY → DESLOPPIFY_SUBJECTIVE → MILESTONE_VALIDATED
      MILESTONE_VALIDATED → MISSION_COMPLETE
    """

    INIT = "init"
    PLANNING = "planning"
    DIFFICULTY_CLASSIFIED = "difficulty_classified"
    EXECUTING = "executing"
    MECHANICAL_CHECKS = "mechanical_checks"
    ORACLE_GENERATED = "oracle_generated"
    UNDER_REVIEW = "under_review"
    VERDICT_PASS = "verdict_pass"
    VERDICT_FAIL = "verdict_fail"
    PROPOSE_COMMIT = "propose_commit"
    SHADOW_MERGE = "shadow_merge"
    ESCALATE_REVIEWER = "escalate_reviewer"
    RECOVERY_MODE = "recovery_mode"
    REWRITE_TASK = "rewrite_task"
    SPLIT_TASK = "split_task"
    ESCALATE_HUMAN = "escalate_human"
    ABORT_TASK = "abort_task"
    DESLOPPIFY_SUBJECTIVE = "desloppify_subjective"
    MILESTONE_BOUNDARY = "milestone_boundary"
    MILESTONE_VALIDATED = "milestone_validated"
    NEXT_TASK = "next_task"
    MISSION_COMPLETE = "mission_complete"
    MERGED = "merged"


class RecoveryDecision(Enum):
    """Recovery mode outcomes.

    When a task fails N times, recovery mode activates and
    the planner decides how to proceed.

    See: §3.3 Recovery Mode
    """

    REWRITE_TASK = "rewrite_task"
    SPLIT_TASK = "split_task"
    CHANGE_APPROACH = "change_approach"
    ESCALATE_HUMAN = "escalate_human"
    ABORT_TASK = "abort_task"


# ---------------------------------------------------------------------------
# State data structures matching §3.2
# ---------------------------------------------------------------------------


@dataclass
class WorkerIdentityState:
    """Worker identity tracking in state."""

    model: str = ""
    lora_version: str | None = None
    endpoint: str = ""
    serving_config: str = ""


@dataclass
class TaskCost:
    """Cost tracking for a single task."""

    local_tokens: int = 0
    frontier_tokens_in: int = 0
    frontier_tokens_out: int = 0
    wall_clock_seconds: int = 0


@dataclass
class TaskTimestamps:
    """Timestamp tracking for task lifecycle events."""

    started: str | None = None
    oracle_generated: str | None = None
    review_started: str | None = None
    verdict_received: str | None = None
    completed: str | None = None


@dataclass
class TaskRecord:
    """Full state record for a single task.

    Matches the task schema in §3.2 state JSON.
    """

    id: str
    description: str
    difficulty_class: str = "uncertain"
    status: str = "init"
    worker_identity: WorkerIdentityState = field(default_factory=WorkerIdentityState)
    iteration: int = 0
    max_iterations: int = 3
    worktree: str = ""
    branch: str = ""
    oracle_id: str | None = None
    verdict_id: str | None = None
    error_taxonomy_tags: list[str] = field(default_factory=list)
    timestamps: TaskTimestamps = field(default_factory=TaskTimestamps)
    cost: TaskCost = field(default_factory=TaskCost)


@dataclass
class DesloppifyState:
    """Desloppify scores for a milestone."""

    mechanical_score: int | None = None
    subjective_score: int | None = None
    last_scan: str | None = None


@dataclass
class MilestoneRecord:
    """State record for a milestone within a mission."""

    id: str
    description: str
    status: str = "pending"
    tasks: list[TaskRecord] = field(default_factory=list)
    desloppify: DesloppifyState = field(default_factory=DesloppifyState)


@dataclass
class MissionRecord:
    """Top-level mission state.

    Schema: forge-state-v0.2
    See: §3.2 State Schema
    """

    id: str
    description: str
    mode: str = "delivery"  # "delivery" | "research"
    status: str = "init"
    created_at: str = ""
    milestones: list[MilestoneRecord] = field(default_factory=list)


@dataclass
class ShadowModeState:
    """Shadow mode state tracking."""

    enabled: bool = True
    pending_merges: list[str] = field(default_factory=list)
    total_proposed: int = 0
    total_approved: int = 0
    total_rejected: int = 0


@dataclass
class RecoveryModeState:
    """Recovery mode state."""

    active: bool = False
    consecutive_failures: int = 0
    threshold: int = 3


@dataclass
class ForgeState:
    """Complete FORGE harness state.

    Persisted to .forge/state.json. Tracks mission, shadow mode,
    recovery mode, and config hash.

    Schema: forge-state-v0.2
    See: §3.2 State Schema
    """

    mission: MissionRecord | None = None
    shadow_mode: ShadowModeState = field(default_factory=ShadowModeState)
    recovery_mode: RecoveryModeState = field(default_factory=RecoveryModeState)
    config_hash: str = ""

    def to_json(self) -> dict[str, Any]:
        """Serialize to JSON for .forge/state.json."""
        # TODO: Implement full serialization matching §3.2 schema
        raise NotImplementedError("ForgeState.to_json not yet implemented")

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> ForgeState:
        """Load state from JSON."""
        # TODO: Implement deserialization with validation
        raise NotImplementedError("ForgeState.from_json not yet implemented")

    @classmethod
    def load(cls, state_path: Path) -> ForgeState:
        """Load state from .forge/state.json.

        Returns empty state if file doesn't exist.
        """
        # TODO: Read and parse .forge/state.json
        raise NotImplementedError("ForgeState.load not yet implemented")

    def save(self, state_path: Path) -> None:
        """Persist state to .forge/state.json."""
        # TODO: Write state as JSON with schema version
        raise NotImplementedError("ForgeState.save not yet implemented")


# ---------------------------------------------------------------------------
# Recovery mode
# ---------------------------------------------------------------------------


@dataclass
class FailureSummary:
    """Summary of failures leading to recovery mode.

    Generated when recovery mode activates after N consecutive
    failures on the same task.

    See: §3.3 Recovery Mode
    """

    task_id: str
    attempts: int
    error_taxonomy_tags: list[str] = field(default_factory=list)
    attempt_summaries: list[dict[str, Any]] = field(default_factory=list)
    patterns: str = ""


# ---------------------------------------------------------------------------
# Mission Control
# ---------------------------------------------------------------------------


class MissionControl:
    """Orchestrates the full task lifecycle.

    Responsibilities (§3.1):
    - Decompose missions into milestones and tasks (via planner model)
    - Classify task difficulty before execution
    - Schedule task execution in isolated git worktrees
    - Manage the Oracle → Review → Verdict → Iterate loop
    - Track state in .forge/state.json
    - Handle recovery mode (rollback, escalate, split)
    - Coordinate Desloppify scans at milestone boundaries
    - Generate daily digests for human sovereign
    - Record all events to observability pipeline

    Usage::

        mc = MissionControl(project_root=Path("."))
        mc.execute_task(description="Implement login endpoint")

    See: FORGE_ARCHITECTURE_v0.2.md §3
    """

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root
        self._state_path = project_root / ".forge" / "state.json"
        self._state: ForgeState | None = None

    def load_state(self) -> ForgeState:
        """Load current state from .forge/state.json.

        TODO: Implement state loading (§3.2).
        """
        raise NotImplementedError("load_state not yet implemented — see §3.2")

    def save_state(self) -> None:
        """Persist current state to .forge/state.json.

        TODO: Implement state persistence (§3.2).
        """
        raise NotImplementedError("save_state not yet implemented — see §3.2")

    def decompose_mission(
        self,
        description: str,
        mode: str = "delivery",
    ) -> MissionRecord:
        """Decompose a mission into milestones and tasks via planner.

        Uses the planner model (DGX Spark #1) to break down the
        mission description into actionable milestones and tasks.

        Args:
            description: Mission description from user.
            mode: "delivery" or "research".

        Returns:
            MissionRecord with decomposed milestones/tasks.

        TODO: Implement planner-based decomposition (§3.1).
        TODO: Generate unique mission/milestone/task IDs.
        """
        raise NotImplementedError("decompose_mission not yet implemented — see §3.1")

    def execute_task(
        self,
        description: str,
        difficulty_override: str | None = None,
    ) -> None:
        """Execute a single task through the full lifecycle.

        The main orchestration loop:
        1. Classify difficulty
        2. Create worktree
        3. Execute worker in worktree
        4. Run mechanical checks
        5. Generate Oracle
        6. Send to reviewer
        7. Handle verdict (iterate or commit)

        Args:
            description: Task description.
            difficulty_override: Manual difficulty class override.

        TODO: Implement the full task loop (§3, §1.3 state machine).
        TODO: Wire up Oracle Generator (§4).
        TODO: Wire up Gate Engine (§5).
        TODO: Wire up Enforcement Layer (§6).
        TODO: Record all events in observability pipeline (§10).
        """
        raise NotImplementedError("execute_task not yet implemented — see §3")

    def handle_verdict(
        self,
        task: TaskRecord,
        verdict: Any,  # Verdict type — avoids circular import
    ) -> TaskState:
        """Process a verdict and determine next state.

        PASS → PROPOSE_COMMIT
        FAIL (iteration < N) → EXECUTING with TODO
        FAIL (iteration == 2) → ESCALATE_REVIEWER
        FAIL (iteration >= 3) → RECOVERY_MODE

        Args:
            task: Current task record.
            verdict: The verdict from the reviewer.

        Returns:
            Next TaskState.

        TODO: Implement verdict handling logic (§5.3).
        """
        raise NotImplementedError("handle_verdict not yet implemented — see §5.3")

    def enter_recovery_mode(self, task: TaskRecord) -> RecoveryDecision:
        """Activate recovery mode after N consecutive failures.

        Recovery sequence (§3.3):
        1. Stop iteration
        2. Generate failure summary
        3. Escalate to planner/frontier
        4. Rollback to last clean commit
        5. If rewritten/split: new tasks enter PLANNING

        Args:
            task: The failing task record.

        Returns:
            RecoveryDecision enum value.

        TODO: Implement recovery mode (§3.3).
        TODO: Generate FailureSummary with all attempt data.
        TODO: Send to planner for rewrite/split decision.
        """
        raise NotImplementedError("enter_recovery_mode not yet implemented — see §3.3")

    def create_worktree(self, task_id: str, task_slug: str) -> Path:
        """Create an isolated git worktree for a task.

        Every active task runs in an isolated worktree (§12.2):
        `git worktree add .forge-worktrees/<task-slug> -b forge/<task-id>`

        Args:
            task_id: Task identifier.
            task_slug: Human-readable slug for directory name.

        Returns:
            Path to the created worktree.

        TODO: Implement worktree creation (§12.2).
        """
        raise NotImplementedError("create_worktree not yet implemented — see §12.2")

    def cleanup_worktree(self, worktree_path: Path) -> None:
        """Remove a task's worktree after completion or abort.

        TODO: Implement worktree cleanup (§12.2).
        """
        raise NotImplementedError("cleanup_worktree not yet implemented — see §12.2")

    def run_main_loop(self) -> None:
        """Main orchestration loop for mission execution.

        Iterates through milestones and tasks, managing the full
        lifecycle for each. Coordinates Desloppify subjective scans
        at milestone boundaries.

        TODO: Implement the main loop (§3).
        TODO: Handle milestone boundary Desloppify subjective scans (§6.4).
        TODO: Generate daily digests (§10.4).
        """
        raise NotImplementedError("run_main_loop not yet implemented — see §3")

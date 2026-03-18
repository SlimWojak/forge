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

import json
import re
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
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
        result: dict[str, Any] = {
            "$schema": "forge-oracle-v0.2",
            "oracle_version": self.oracle_version,
            "oracle_id": self.oracle_id,
            "timestamp": self.timestamp,
        }
        if self.task_context:
            result["task_context"] = asdict(self.task_context)
        if self.worker_identity:
            result["worker_identity"] = asdict(self.worker_identity)
        if self.diff_summary:
            result["diff_summary"] = asdict(self.diff_summary)
        if self.codemap:
            result["codemap"] = {
                "changed_files": [asdict(f) for f in self.codemap.changed_files],
                "affected_files": [asdict(f) for f in self.codemap.affected_files],
            }
        if self.mechanical_checks:
            mc = {}
            for check_name in ("lint", "type_check", "tests", "build"):
                val = getattr(self.mechanical_checks, check_name)
                if val is not None:
                    mc[check_name] = asdict(val)
            mc["desloppify_mechanical"] = self.mechanical_checks.desloppify_mechanical
            result["mechanical_checks"] = mc
        if self.quality_delta:
            result["quality_delta"] = asdict(self.quality_delta)
        if self.worker_self_assessment:
            result["worker_self_assessment"] = asdict(self.worker_self_assessment)
        result["available_annexes"] = self.available_annexes
        return result

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> CoreOracle:
        """Deserialize from JSON dict."""
        oracle = cls(
            oracle_version=data.get("oracle_version", "0.2"),
            oracle_id=data.get("oracle_id", ""),
            timestamp=data.get("timestamp", ""),
        )
        if "task_context" in data:
            oracle.task_context = TaskContext(**data["task_context"])
        if "diff_summary" in data:
            oracle.diff_summary = DiffSummary(**data["diff_summary"])
        oracle.available_annexes = data.get("available_annexes", [])
        return oracle


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
        self._oracle_dir.mkdir(parents=True, exist_ok=True)

    def generate_diff(
        self,
        worktree_path: Path,
        main_branch: str = "main",
    ) -> tuple[DiffSummary, str]:
        """Step 1: Compute git diff against main branch.

        Returns:
            Tuple of (DiffSummary, raw diff text for annexes).

        See: §4.4 step 1
        """
        diff_cmd = subprocess.run(
            ["git", "diff", "--stat", main_branch],
            capture_output=True, text=True,
            cwd=str(worktree_path),
        )
        full_diff_cmd = subprocess.run(
            ["git", "diff", main_branch],
            capture_output=True, text=True,
            cwd=str(worktree_path),
        )
        raw_diff = full_diff_cmd.stdout

        files_changed = files_added = files_deleted = 0
        insertions = deletions = 0
        stat_output = diff_cmd.stdout

        for line in stat_output.strip().splitlines():
            if "|" in line:
                files_changed += 1
            if "file changed" in line or "files changed" in line:
                ins_m = re.search(r"(\d+) insertion", line)
                del_m = re.search(r"(\d+) deletion", line)
                if ins_m:
                    insertions = int(ins_m.group(1))
                if del_m:
                    deletions = int(del_m.group(1))

        # Parse changed file list
        name_cmd = subprocess.run(
            ["git", "diff", "--name-status", main_branch],
            capture_output=True, text=True,
            cwd=str(worktree_path),
        )
        for line in name_cmd.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                status = parts[0]
                if status.startswith("A"):
                    files_added += 1
                elif status.startswith("D"):
                    files_deleted += 1

        # Extract function-level changes from diff hunks
        funcs_added: list[str] = []
        funcs_modified: list[str] = []
        for line in raw_diff.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                stripped = line[1:].strip()
                if stripped.startswith("def ") or stripped.startswith("class "):
                    sig = stripped.split("(")[0] if "(" in stripped else stripped
                    sig = sig.split(":")[0]
                    funcs_added.append(sig)
                elif (
                    stripped.startswith("function ")
                    or stripped.startswith("export function ")
                ):
                    sig = stripped.split("(")[0] if "(" in stripped else stripped
                    funcs_added.append(sig)

        return DiffSummary(
            files_changed=files_changed,
            files_added=files_added,
            files_deleted=files_deleted,
            insertions=insertions,
            deletions=deletions,
            functions_added=funcs_added,
            functions_modified=funcs_modified,
            functions_deleted=[],
        ), raw_diff

    def generate_codemap(
        self,
        changed_files: list[str],
        worktree_path: Path,
    ) -> Codemap:
        """Steps 2-3: Tree-sitter parse + dependency analysis.

        See: §4.4 steps 2-3
        """
        from forge.aci.tools import codemap as run_codemap

        abs_paths = []
        for f in changed_files:
            p = Path(f)
            if not p.is_absolute():
                p = worktree_path / p
            if p.is_file():
                abs_paths.append(str(p))

        cm_result = run_codemap(abs_paths)

        changed: list[ChangedFile] = []
        for file_data in cm_result.files:
            sigs = [s["signature"] for s in file_data.get("symbols", [])]
            imports = [
                s["name"] for s in file_data.get("symbols", [])
                if s.get("kind") == "import"
            ]
            exports = [
                s["name"] for s in file_data.get("symbols", [])
                if s.get("kind") == "export"
            ]
            changed.append(ChangedFile(
                path=file_data["path"],
                language=file_data.get("language", "unknown"),
                signatures=sigs,
                imports_added=imports,
                exports_added=exports,
            ))

        return Codemap(changed_files=changed, affected_files=[])

    def run_mechanical_checks(
        self,
        worktree_path: Path,
    ) -> MechanicalChecks:
        """Step 4: Run lint, typecheck, test suite.

        See: §4.4 step 4
        """
        from forge.aci.tools import run_command, run_tests

        # Lint check
        lint_result = run_command(
            "python -m ruff check .",
            timeout=30,
            cwd=str(worktree_path),
        )
        lint_check = MechanicalCheckResult(
            status="pass" if lint_result.exit_code == 0 else "fail",
            errors=lint_result.stdout.count("error") if lint_result.exit_code != 0 else 0,
            warnings=0,
        )

        # Tests
        test_result = run_tests(cwd=str(worktree_path))
        test_check = MechanicalCheckResult(
            status="pass" if test_result.status == "pass" else "fail",
            errors=test_result.failed,
            details={
                "passed": test_result.passed,
                "failed": test_result.failed,
                "skipped": test_result.skipped,
            },
        )

        return MechanicalChecks(
            lint=lint_check,
            tests=test_check,
        )

    def get_quality_delta(
        self,
        worktree_path: Path,
        changed_files: list[str],
    ) -> QualityDelta:
        """Step 5: Placeholder quality delta (Desloppify is F015).

        See: §4.4 step 5
        """
        return QualityDelta(
            desloppify_mechanical_score=0,
            delta_from_previous="+0",
            new_issues=[],
            resolved_issues=[],
        )

    def prompt_worker_self_assessment(
        self,
        worker_final_message: str,
    ) -> WorkerSelfAssessment:
        """Step 6: Extract structured self-assessment from worker.

        Attempts to parse JSON from the worker's final message.
        Falls back to a default assessment if parsing fails.

        See: §4.4 step 6
        """
        try:
            json_match = re.search(
                r"\{[^{}]*\"confidence\"[^{}]*\}",
                worker_final_message,
                re.DOTALL,
            )
            if json_match:
                data = json.loads(json_match.group())
                return WorkerSelfAssessment(
                    confidence=data.get("confidence", "medium"),
                    concerns=data.get("concerns", []),
                    decisions_made=data.get("decisions_made", []),
                )
        except (json.JSONDecodeError, AttributeError):
            pass

        return WorkerSelfAssessment(
            confidence="medium",
            concerns=[],
            decisions_made=[],
        )

    def _get_changed_file_paths(
        self,
        worktree_path: Path,
        main_branch: str,
    ) -> list[str]:
        """Get list of changed file paths from git diff."""
        result = subprocess.run(
            ["git", "diff", "--name-only", main_branch],
            capture_output=True, text=True,
            cwd=str(worktree_path),
        )
        return [
            line.strip() for line in result.stdout.strip().splitlines()
            if line.strip()
        ]

    def build_oracle(
        self,
        task_id: str,
        worktree_path: Path,
        main_branch: str = "main",
        worker_final_message: str = "",
        task_context: TaskContext | None = None,
        worker_identity: WorkerIdentity | None = None,
        iteration: int = 1,
    ) -> CoreOracle:
        """Execute the full Oracle generation pipeline (§4.4).

        See: §4.4
        """
        gen_start = time.monotonic()
        now = datetime.now(UTC).isoformat()
        oracle_id = f"oracle-{task_id}-iter-{iteration}"

        # Step 1: git diff
        diff_summary, raw_diff = self.generate_diff(worktree_path, main_branch)

        # Steps 2-3: tree-sitter codemap + dependency analysis
        changed_paths = self._get_changed_file_paths(worktree_path, main_branch)
        codemap_data = self.generate_codemap(changed_paths, worktree_path)

        # Step 4: mechanical checks
        mech_checks = self.run_mechanical_checks(worktree_path)

        # Step 5: quality delta
        quality = self.get_quality_delta(worktree_path, changed_paths)

        # Step 6: worker self-assessment
        self_assess = self.prompt_worker_self_assessment(worker_final_message)

        # Step 8: stage annexes
        annexes = self._stage_annexes(
            oracle_id, worktree_path, raw_diff, "", []
        )

        # Step 7: assemble Core Oracle
        oracle = CoreOracle(
            oracle_id=oracle_id,
            timestamp=now,
            task_context=task_context,
            worker_identity=worker_identity,
            diff_summary=diff_summary,
            codemap=codemap_data,
            mechanical_checks=mech_checks,
            quality_delta=quality,
            worker_self_assessment=self_assess,
            available_annexes=annexes,
        )

        # Persist Core Oracle
        oracle_dir = self._oracle_dir / oracle_id
        oracle_dir.mkdir(parents=True, exist_ok=True)
        core_path = oracle_dir / "core.json"
        core_path.write_text(
            json.dumps(oracle.to_json(), indent=2),
            encoding="utf-8",
        )

        # Persist metadata
        gen_ms = int((time.monotonic() - gen_start) * 1000)
        metadata = OracleMetadata(
            oracle_id=oracle_id,
            generation_started=now,
            generation_completed=datetime.now(UTC).isoformat(),
            generation_duration_ms=gen_ms,
            treesitter_parse_ms=0,
            diff_computation_ms=0,
            mechanical_checks_ms=0,
            total_token_estimate=len(json.dumps(oracle.to_json())) // 4,
        )
        meta_path = oracle_dir / "metadata.json"
        meta_path.write_text(
            json.dumps(asdict(metadata), indent=2),
            encoding="utf-8",
        )

        return oracle

    def _stage_annexes(
        self,
        oracle_id: str,
        worktree_path: Path,
        diff_text: str,
        test_output: str,
        prior_verdicts: list[dict[str, Any]],
    ) -> list[str]:
        """Step 8: Stage Tier 2 annexes to disk.

        See: §4.3
        """
        oracle_dir = self._oracle_dir / oracle_id / "annexes"
        oracle_dir.mkdir(parents=True, exist_ok=True)
        available: list[str] = []

        if diff_text:
            (oracle_dir / "full_patch.diff").write_text(diff_text)
            available.append("full_patch")

        if test_output:
            (oracle_dir / "test_output.txt").write_text(test_output)
            available.append("test_output")

        if prior_verdicts:
            (oracle_dir / "prior_verdicts.json").write_text(
                json.dumps(prior_verdicts, indent=2)
            )
            available.append("prior_verdicts")

        return available

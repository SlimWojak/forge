"""Tests for FORGE Task Iteration Loop (F010).

Uses mock worker, oracle builder, and gate to test the full
orchestration without requiring real models or git repos.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from forge.gate.engine import (
    GateEngine,
    VerdictOutcome,
)
from forge.oracle.generator import CoreOracle, DiffSummary
from forge.orchestrator.task_loop import (
    LoopResult,
    WorkerOutput,
    run_task_loop,
)

# ---------------------------------------------------------------------------
# Mock components
# ---------------------------------------------------------------------------


class MockWorker:
    """Worker that always completes successfully."""

    def __init__(self, tool_calls: int = 5) -> None:
        self._tool_calls = tool_calls
        self.call_count = 0

    def run(
        self,
        task_description: str,
        todo_context: str | None = None,
    ) -> WorkerOutput:
        self.call_count += 1
        return WorkerOutput(
            completed=True,
            final_message="Task complete. All changes made and tested.",
            tool_calls_count=self._tool_calls,
        )


class MockFailingWorker:
    """Worker that returns errors."""

    def run(
        self,
        task_description: str,
        todo_context: str | None = None,
    ) -> WorkerOutput:
        return WorkerOutput(
            completed=False,
            error="Context window exhausted",
            tool_calls_count=0,
        )


class MockOracleBuilder:
    """Oracle builder that returns a minimal oracle."""

    def __init__(self) -> None:
        self.build_count = 0

    def build(
        self,
        task_id: str,
        iteration: int,
        worker_message: str,
    ) -> CoreOracle:
        self.build_count += 1
        return CoreOracle(
            oracle_id=f"oracle-{task_id}-iter-{iteration}",
            timestamp="2026-03-18T10:00:00Z",
            diff_summary=DiffSummary(
                files_changed=2, files_added=1, files_deleted=0,
                insertions=50, deletions=10,
            ),
        )


class MockPassReviewer:
    """Reviewer that always passes."""

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "verdict": "PASS",
                        "error_taxonomy_tags": [],
                        "summary": "Implementation looks correct.",
                        "issues": [],
                    })
                }
            }]
        }


class MockFailReviewer:
    """Reviewer that always fails with structured issues."""

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "verdict": "FAIL",
                        "error_taxonomy_tags": ["missing-tests"],
                        "summary": "Missing error case tests.",
                        "issues": [
                            {
                                "id": "issue-001",
                                "file": "src/app.py",
                                "line_range": [10, 20],
                                "severity": "blocking",
                                "category": "missing-tests",
                                "what": "No error case test",
                                "why": "Must handle errors",
                                "fix": "Add error test",
                                "acceptance_criteria": "Test passes",
                            }
                        ],
                    })
                }
            }]
        }


class MockFailThenPassReviewer:
    """Reviewer that fails first, then passes."""

    def __init__(self) -> None:
        self._call_count = 0

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self._call_count += 1
        if self._call_count == 1:
            return {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "verdict": "FAIL",
                            "error_taxonomy_tags": ["missing-tests"],
                            "summary": "Needs more tests.",
                            "issues": [
                                {
                                    "id": "issue-001",
                                    "file": "src/app.py",
                                    "line_range": [1, 5],
                                    "severity": "blocking",
                                    "category": "missing-tests",
                                    "what": "Missing test",
                                    "why": "Coverage needed",
                                    "fix": "Add test",
                                    "acceptance_criteria": "Test passes",
                                }
                            ],
                        })
                    }
                }]
            }
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "verdict": "PASS",
                        "error_taxonomy_tags": [],
                        "summary": "Issues fixed. Looks good now.",
                        "issues": [],
                    })
                }
            }]
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def loop_project(tmp_path: Path) -> Path:
    """Create a project directory for the loop tests."""
    forge_dir = tmp_path / ".forge"
    forge_dir.mkdir()
    (forge_dir / "verdicts").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# F010: Task iteration loop
# ---------------------------------------------------------------------------


class TestLoopPassFirstTry:
    """test_loop_pass_first_try — happy path."""

    def test_returns_loop_result(self, loop_project: Path) -> None:
        gate = GateEngine(
            project_root=loop_project,
            reviewer=MockPassReviewer(),
        )
        result = run_task_loop(
            task_id="001",
            task_description="Add greeting function",
            worker=MockWorker(),
            oracle_builder=MockOracleBuilder(),
            gate=gate,
        )
        assert isinstance(result, LoopResult)

    def test_passes_first_try(self, loop_project: Path) -> None:
        gate = GateEngine(
            project_root=loop_project,
            reviewer=MockPassReviewer(),
        )
        result = run_task_loop(
            task_id="001",
            task_description="Add greeting function",
            worker=MockWorker(),
            oracle_builder=MockOracleBuilder(),
            gate=gate,
        )
        assert result.passed is True
        assert result.iterations == 1
        assert result.recovery_mode is False

    def test_has_proposal(self, loop_project: Path) -> None:
        gate = GateEngine(
            project_root=loop_project,
            reviewer=MockPassReviewer(),
        )
        result = run_task_loop(
            task_id="001",
            task_description="Add greeting function",
            worker=MockWorker(),
            oracle_builder=MockOracleBuilder(),
            gate=gate,
        )
        assert result.proposal is not None
        assert result.proposal["task_id"] == "001"
        assert result.proposal["verdict"] == "PASS"
        assert result.proposal["shadow_mode"] is True

    def test_records_timing(self, loop_project: Path) -> None:
        gate = GateEngine(
            project_root=loop_project,
            reviewer=MockPassReviewer(),
        )
        result = run_task_loop(
            task_id="001",
            task_description="Add greeting function",
            worker=MockWorker(tool_calls=10),
            oracle_builder=MockOracleBuilder(),
            gate=gate,
        )
        assert result.wall_clock_ms >= 0
        assert result.total_tool_calls == 10

    def test_has_verdict(self, loop_project: Path) -> None:
        gate = GateEngine(
            project_root=loop_project,
            reviewer=MockPassReviewer(),
        )
        result = run_task_loop(
            task_id="001",
            task_description="Add greeting function",
            worker=MockWorker(),
            oracle_builder=MockOracleBuilder(),
            gate=gate,
        )
        assert result.final_verdict is not None
        assert result.final_verdict.verdict == VerdictOutcome.PASS


class TestLoopFailThenPass:
    """test_loop_fail_then_pass — iteration on failure."""

    def test_passes_on_second_try(self, loop_project: Path) -> None:
        gate = GateEngine(
            project_root=loop_project,
            reviewer=MockFailThenPassReviewer(),
        )
        worker = MockWorker()
        oracle_builder = MockOracleBuilder()
        result = run_task_loop(
            task_id="002",
            task_description="Implement login endpoint",
            worker=worker,
            oracle_builder=oracle_builder,
            gate=gate,
        )
        assert result.passed is True
        assert result.iterations == 2

    def test_worker_called_twice(self, loop_project: Path) -> None:
        gate = GateEngine(
            project_root=loop_project,
            reviewer=MockFailThenPassReviewer(),
        )
        worker = MockWorker()
        run_task_loop(
            task_id="002",
            task_description="Implement login endpoint",
            worker=worker,
            oracle_builder=MockOracleBuilder(),
            gate=gate,
        )
        assert worker.call_count == 2

    def test_oracle_built_twice(self, loop_project: Path) -> None:
        gate = GateEngine(
            project_root=loop_project,
            reviewer=MockFailThenPassReviewer(),
        )
        oracle_builder = MockOracleBuilder()
        run_task_loop(
            task_id="002",
            task_description="Implement login endpoint",
            worker=MockWorker(),
            oracle_builder=oracle_builder,
            gate=gate,
        )
        assert oracle_builder.build_count == 2

    def test_accumulates_tool_calls(self, loop_project: Path) -> None:
        gate = GateEngine(
            project_root=loop_project,
            reviewer=MockFailThenPassReviewer(),
        )
        result = run_task_loop(
            task_id="002",
            task_description="Implement login endpoint",
            worker=MockWorker(tool_calls=8),
            oracle_builder=MockOracleBuilder(),
            gate=gate,
        )
        assert result.total_tool_calls == 16  # 8 per iteration x 2


class TestLoopRecoveryMode:
    """test_loop_recovery_mode — consecutive failures trigger recovery."""

    def test_enters_recovery_after_3_failures(self, loop_project: Path) -> None:
        gate = GateEngine(
            project_root=loop_project,
            reviewer=MockFailReviewer(),
        )
        result = run_task_loop(
            task_id="003",
            task_description="Complex refactoring",
            worker=MockWorker(),
            oracle_builder=MockOracleBuilder(),
            gate=gate,
            max_iterations=3,
        )
        assert result.passed is False
        assert result.recovery_mode is True
        assert result.iterations == 3

    def test_recovery_has_failure_summary(self, loop_project: Path) -> None:
        gate = GateEngine(
            project_root=loop_project,
            reviewer=MockFailReviewer(),
        )
        result = run_task_loop(
            task_id="003",
            task_description="Complex refactoring",
            worker=MockWorker(),
            oracle_builder=MockOracleBuilder(),
            gate=gate,
            max_iterations=3,
        )
        assert result.failure_summary != ""
        assert "Recovery mode" in result.failure_summary

    def test_worker_error_triggers_recovery(self, loop_project: Path) -> None:
        gate = GateEngine(
            project_root=loop_project,
            reviewer=MockPassReviewer(),
        )
        result = run_task_loop(
            task_id="004",
            task_description="Broken task",
            worker=MockFailingWorker(),
            oracle_builder=MockOracleBuilder(),
            gate=gate,
            max_iterations=3,
        )
        assert result.passed is False
        assert result.recovery_mode is True
        assert "Worker error" in result.failure_summary

    def test_does_not_thrash(self, loop_project: Path) -> None:
        gate = GateEngine(
            project_root=loop_project,
            reviewer=MockFailReviewer(),
        )
        worker = MockWorker()
        result = run_task_loop(
            task_id="005",
            task_description="Impossible task",
            worker=worker,
            oracle_builder=MockOracleBuilder(),
            gate=gate,
            max_iterations=3,
        )
        # Worker should be called exactly 3 times, then stop
        assert worker.call_count == 3
        assert result.iterations == 3

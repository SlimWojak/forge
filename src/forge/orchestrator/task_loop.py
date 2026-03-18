"""FORGE Task Iteration Loop — the complete orchestration pipeline.

Wires together: Worker -> Oracle -> Gate -> Verdict -> Iterate/Merge.

This is the core execution loop described in §3 and §5.3:
  1. Worker executes task using ACI tools
  2. Oracle generated from the resulting diff
  3. Gate sends Oracle to frontier reviewer
  4. On PASS: propose commit (shadow mode)
  5. On FAIL: feed TODOs back to worker, re-execute, re-oracle, re-review
  6. After 3 consecutive failures: recovery mode (stop)

See: FORGE_ARCHITECTURE_v0.2.md §3, §5.3
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol

from forge.gate.engine import GateEngine, VerdictOutcome

# ---------------------------------------------------------------------------
# Protocols for injectable dependencies
# ---------------------------------------------------------------------------


class WorkerRunner(Protocol):
    """Protocol for the worker execution backend."""

    def run(
        self,
        task_description: str,
        todo_context: str | None = None,
    ) -> WorkerOutput:
        ...


class OracleBuilder(Protocol):
    """Protocol for the oracle generation backend."""

    def build(
        self,
        task_id: str,
        iteration: int,
        worker_message: str,
    ) -> Any:
        ...


@dataclass
class WorkerOutput:
    """Simplified output from the worker for the loop."""

    completed: bool
    final_message: str = ""
    tool_calls_count: int = 0
    error: str | None = None


# ---------------------------------------------------------------------------
# Loop result
# ---------------------------------------------------------------------------


@dataclass
class LoopResult:
    """Result of a complete task iteration loop."""

    task_id: str
    task_description: str
    passed: bool
    iterations: int
    recovery_mode: bool = False
    final_verdict: Any | None = None
    proposal: dict[str, Any] | None = None
    failure_summary: str = ""
    wall_clock_ms: int = 0
    total_tool_calls: int = 0
    tokens_local_estimate: int = 0
    tokens_frontier_estimate: int = 0


# ---------------------------------------------------------------------------
# Task iteration loop
# ---------------------------------------------------------------------------


def run_task_loop(
    task_id: str,
    task_description: str,
    worker: WorkerRunner,
    oracle_builder: OracleBuilder,
    gate: GateEngine,
    max_iterations: int = 3,
) -> LoopResult:
    """Execute the full task iteration loop.

    The loop:
      1. Worker executes task
      2. Oracle generated from diff
      3. Gate reviews Oracle
      4. PASS -> propose commit, return
      5. FAIL -> extract TODOs, feed back to worker, repeat from 1
      6. After max_iterations failures -> recovery mode, return

    Args:
        task_id: Unique task identifier.
        task_description: What the worker should implement.
        worker: Worker execution backend.
        oracle_builder: Oracle generation backend.
        gate: Gate engine for frontier review.
        max_iterations: Max review iterations before recovery. Default 3.

    Returns:
        LoopResult with pass/fail status, iteration count, and verdict.

    See: FORGE_ARCHITECTURE_v0.2.md §3, §5.3
    """
    start = time.monotonic()
    total_tool_calls = 0
    todo_context: str | None = None

    for iteration in range(1, max_iterations + 1):
        # Step 1: Worker executes
        worker_output = worker.run(
            task_description=task_description,
            todo_context=todo_context,
        )
        total_tool_calls += worker_output.tool_calls_count

        if not worker_output.completed and worker_output.error:
            # Worker failed internally
            if iteration >= max_iterations:
                return LoopResult(
                    task_id=task_id,
                    task_description=task_description,
                    passed=False,
                    iterations=iteration,
                    recovery_mode=True,
                    failure_summary=f"Worker error: {worker_output.error}",
                    wall_clock_ms=int((time.monotonic() - start) * 1000),
                    total_tool_calls=total_tool_calls,
                )
            continue

        # Step 2: Oracle generated
        oracle = oracle_builder.build(
            task_id=task_id,
            iteration=iteration,
            worker_message=worker_output.final_message,
        )

        # Step 3: Gate reviews
        verdict = gate.send_to_reviewer(
            oracle=oracle,
            iteration=iteration,
            task_id=task_id,
        )

        # Step 4: Check verdict
        if verdict.verdict == VerdictOutcome.PASS:
            # Shadow mode: propose commit
            proposal = gate.propose_commit(task_id, verdict)
            elapsed = int((time.monotonic() - start) * 1000)
            return LoopResult(
                task_id=task_id,
                task_description=task_description,
                passed=True,
                iterations=iteration,
                final_verdict=verdict,
                proposal=proposal,
                wall_clock_ms=elapsed,
                total_tool_calls=total_tool_calls,
            )

        # Step 5: FAIL — check for recovery mode
        if gate.should_enter_recovery(iteration):
            elapsed = int((time.monotonic() - start) * 1000)
            return LoopResult(
                task_id=task_id,
                task_description=task_description,
                passed=False,
                iterations=iteration,
                recovery_mode=True,
                final_verdict=verdict,
                failure_summary=(
                    f"Recovery mode after {iteration} consecutive failures. "
                    f"Last verdict: {verdict.summary}"
                ),
                wall_clock_ms=elapsed,
                total_tool_calls=total_tool_calls,
            )

        # Step 6: Extract TODOs and feed back to worker
        todos = gate.extract_todos_from_verdict(verdict)
        if todos:
            todo_lines = []
            for t in todos:
                todo_lines.append(
                    f"- [{t['file']}] {t['what']}: {t['fix']}"
                )
            todo_context = (
                "Previous review FAILED. Fix these issues:\n"
                + "\n".join(todo_lines)
            )
        else:
            todo_context = f"Previous review FAILED: {verdict.summary}"

    # Should not reach here, but safety net
    elapsed = int((time.monotonic() - start) * 1000)
    return LoopResult(
        task_id=task_id,
        task_description=task_description,
        passed=False,
        iterations=max_iterations,
        recovery_mode=True,
        failure_summary="Max iterations exhausted",
        wall_clock_ms=elapsed,
        total_tool_calls=total_tool_calls,
    )

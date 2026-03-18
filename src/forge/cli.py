"""FORGE CLI — Click-based command-line interface.

Entry point for all FORGE operations. Commands are organized into
groups matching the system architecture:

  - Project lifecycle: init, task, mission, status
  - Quality & review: quality, oracle, review
  - Monitoring: boundary, metrics, config
  - Intervention: intervene, approve, reject, replan

See: FORGE_ARCHITECTURE_v0.2.md §2
"""

from __future__ import annotations

import click
from rich.console import Console

from forge import __version__

console = Console()


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(version=__version__, prog_name="forge")
@click.pass_context
def main(ctx: click.Context) -> None:
    """FORGE — CLI-first agentic harness for frontier/local model orchestration.

    FORGE orchestrates local and frontier LLMs to build software. It measures
    the empirical boundary between where local models suffice and where frontier
    judgment is required.

    Use 'forge <command> --help' for details on any command.
    """
    ctx.ensure_object(dict)


# ---------------------------------------------------------------------------
# Project Lifecycle
# ---------------------------------------------------------------------------


@main.command()
@click.argument("project_name")
def init(project_name: str) -> None:
    """Scaffold a new project with .forge/ state directory.

    Creates the .forge/ directory structure, default config.yaml,
    hooks.yaml, architecture.yaml, and initial state.json.

    See: FORGE_ARCHITECTURE_v0.2.md §2.1, §12.1
    """
    # TODO: Create .forge/ directory tree (§12.1)
    # TODO: Write default config.yaml (§13.1)
    # TODO: Write default hooks.yaml (§6.1)
    # TODO: Write default architecture.yaml (§6.2)
    # TODO: Initialize state.json with empty mission
    # TODO: Initialize DuckDB trace database (§10.2)
    console.print(f"[bold green]FORGE[/] Initialized project: {project_name}")
    console.print("Created .forge/ directory with default configuration.")
    console.print("Not yet implemented — see §2.1 for full init spec.")


@main.command()
@click.argument("description")
@click.option(
    "--difficulty",
    type=click.Choice(["mechanical", "local-reasoning", "architectural", "uncertain"]),
    default=None,
    help="Manual difficulty override (default: planner classifies).",
)
def task(description: str, difficulty: str | None) -> None:
    """Execute a single task (simpler loop, no milestones).

    The task goes through the full lifecycle:
    plan \u2192 execute \u2192 oracle \u2192 review \u2192 verdict \u2192 iterate/commit.

    Difficulty is classified by the planner model unless overridden
    with --difficulty.

    See: FORGE_ARCHITECTURE_v0.2.md \xa72.1, \xa73
    """
    import os
    import uuid
    from pathlib import Path

    from forge.aci.worker import run_worker
    from forge.config.loader import load_config
    from forge.gate.engine import GateEngine
    from forge.models.adapter import LocalModelAdapter
    from forge.models.provider import ModelProvider
    from forge.oracle.generator import OracleGenerator
    from forge.orchestrator.task_loop import WorkerOutput, run_task_loop

    project_root = Path(".")
    console.print(f"[bold green]FORGE[/] Task: {description}")

    try:
        cfg = load_config(project_root)
    except FileNotFoundError:
        console.print("[red]Error:[/] .forge/config.yaml not found. Run forge init first.")
        raise SystemExit(1)

    provider = ModelProvider(config=cfg)
    worker_adapter = LocalModelAdapter(provider, role="worker")

    if os.environ.get("ANTHROPIC_API_KEY"):
        reviewer_adapter = LocalModelAdapter(provider, role="reviewer")
    else:
        console.print("  [yellow]No ANTHROPIC_API_KEY \u2014 using local model as reviewer[/]")
        reviewer_adapter = LocalModelAdapter(provider, role="worker")

    task_id = f"task-{uuid.uuid4().hex[:8]}"
    cwd = str(project_root.resolve())

    class _WorkerRunnerImpl:
        def run(self, task_description: str, todo_context: str | None = None) -> WorkerOutput:
            full_desc = task_description
            if todo_context:
                full_desc = task_description + "\n\n" + todo_context
            console.print("  [cyan]Worker executing...[/]")
            result = run_worker(full_desc, model=worker_adapter, cwd=cwd)
            console.print(
                f"  [cyan]Worker done:[/] {result.iterations} iter, "
                f"{len(result.tool_calls)} tool calls"
            )
            if result.error:
                console.print(f"  [red]Worker error:[/] {result.error}")
            return WorkerOutput(
                completed=result.completed,
                final_message=result.final_message or "",
                tool_calls_count=len(result.tool_calls),
                error=result.error,
            )

    class _OracleBuilderImpl:
        def __init__(self):
            self._gen = OracleGenerator(project_root=project_root)

        def build(self, task_id: str, iteration: int, worker_message: str):
            console.print(f"  [yellow]Generating Oracle (iteration {iteration})...[/]")
            try:
                orc = self._gen.build_oracle(
                    task_id=task_id,
                    worktree_path=project_root,
                    main_branch="HEAD~1",
                    worker_final_message=worker_message,
                    iteration=iteration,
                )
                console.print("  [yellow]Oracle ready[/]")
                return orc
            except Exception as e:
                console.print(f"  [red]Oracle error:[/] {e}")
                raise

    gate = GateEngine(
        config=cfg.get("gate", {}),
        project_root=project_root,
        reviewer=reviewer_adapter,
    )

    console.print(f"  Task ID: {task_id}")
    if difficulty:
        console.print(f"  Difficulty override: {difficulty}")

    result = run_task_loop(
        task_id=task_id,
        task_description=description,
        worker=_WorkerRunnerImpl(),
        oracle_builder=_OracleBuilderImpl(),
        gate=gate,
        max_iterations=cfg.get("gate", {}).get("max_iterations", 3),
    )

    if result.passed:
        console.print(f"\n[bold green]PASS[/] after {result.iterations} iteration(s)")
        console.print(f"  Wall clock: {result.wall_clock_ms:,}ms")
        console.print(f"  Tool calls: {result.total_tool_calls}")
        if result.proposal:
            console.print("  [yellow]Shadow mode:[/] Commit proposed.")
    else:
        console.print(f"\n[bold red]FAIL[/] after {result.iterations} iteration(s)")
        if result.recovery_mode:
            console.print("  [red]Recovery mode activated[/]")
        if result.failure_summary:
            console.print(f"  {result.failure_summary}")
        console.print(f"  Wall clock: {result.wall_clock_ms:,}ms")


@main.command()
@click.argument("description")
@click.option(
    "--mode",
    type=click.Choice(["delivery", "research"]),
    default="delivery",
    help="Mission class (default: delivery).",
)
def mission(description: str, mode: str) -> None:
    """Start a multi-milestone mission (Phase 2+, stub only).

    Decomposes the mission into milestones and tasks via the planner
    model, then executes them sequentially with full orchestration.

    Phase 1: Stub only. Use 'forge task' for single-task execution.
    Phase 2+: Full mission decomposition and parallel execution.

    See: FORGE_ARCHITECTURE_v0.2.md §2.1, §3
    """
    # TODO: Phase 2+ — decompose mission into milestones
    # TODO: Phase 2+ — schedule milestones and track state
    console.print(f"[bold green]FORGE[/] Mission: {description} (mode={mode})")
    console.print("Not yet implemented — Phase 2+ feature. Use 'forge task' for now.")


@main.command()
def status() -> None:
    """Show current state: active tasks, quality, loop metrics, phase.

    See: FORGE_ARCHITECTURE_v0.2.md §2.1, §3.2
    """
    import json
    from pathlib import Path

    state_path = Path(".forge/state.json")
    feature_path = Path("feature_list.json")

    console.print("[bold green]FORGE[/] Status\n")

    if state_path.exists():
        state = json.loads(state_path.read_text())
        shadow = state.get("shadow_mode", {})
        console.print(f"  Shadow mode: {'enabled' if shadow.get('enabled') else 'disabled'}")
        console.print(f"  Proposed: {shadow.get('total_proposed', 0)}")
        console.print(f"  Approved: {shadow.get('total_approved', 0)}")
    else:
        console.print("  No .forge/state.json found.")

    if feature_path.exists():
        features = json.loads(feature_path.read_text())
        for phase_key in ("phase_1",):
            phase = features.get(phase_key, {})
            for ms_key, ms in phase.items():
                if isinstance(ms, dict) and "features" in ms:
                    total = len(ms["features"])
                    done = sum(1 for f in ms["features"] if f.get("passes"))
                    console.print(f"  {ms.get('name', ms_key)}: {done}/{total}")
    console.print()


# ---------------------------------------------------------------------------
# Quality & Review
# ---------------------------------------------------------------------------


@main.command()
@click.option(
    "--mechanical-only",
    is_flag=True,
    default=False,
    help="Skip LLM subjective review.",
)
def quality(mechanical_only: bool) -> None:
    """Run Desloppify quality scan (mechanical + subjective).

    Mechanical scan uses tree-sitter (zero-GPU, <2s).
    Subjective scan uses the planner LLM at milestone boundaries.

    See: FORGE_ARCHITECTURE_v0.2.md §6.3, §6.4
    """
    import glob

    from forge.enforcement.quality import DesloppifyMechanical

    scanner = DesloppifyMechanical()
    py_files = glob.glob("src/**/*.py", recursive=True)
    result = scanner.scan(py_files)

    console.print(f"[bold green]FORGE[/] Quality: {result.score}/100 ({result.delta})\n")
    if result.issues:
        for issue in result.issues:
            console.print(f"  [{issue.issue_type}] {issue.file}:{issue.line} — {issue.detail}")
    else:
        console.print("  No issues found.")


@main.command()
@click.argument("task_id", required=False)
def oracle(task_id: str | None) -> None:
    """Generate or display the Oracle snapshot for a task.

    The Oracle is a structured 2-4K token snapshot that mediates
    between local workers and frontier reviewers. Frontier models
    never see the full codebase — they see the Oracle.

    See: FORGE_ARCHITECTURE_v0.2.md §4
    """
    import json as _json
    from pathlib import Path as _Path

    from forge.oracle.generator import OracleGenerator

    project_root = _Path(".")
    console.print("[bold green]FORGE[/] Oracle")

    if task_id:
        oracle_dir = project_root / ".forge" / "oracles"
        if oracle_dir.exists():
            matches = list(oracle_dir.glob(f"*{task_id}*.json"))
            if matches:
                data = _json.loads(matches[0].read_text())
                console.print_json(_json.dumps(data, indent=2))
                return
        console.print(f"  No Oracle found for task: {task_id}")
        return

    try:
        gen = OracleGenerator(project_root=project_root)
        oracle_obj = gen.build_oracle(
            task_id="manual",
            worktree_path=project_root,
            main_branch="HEAD~1",
            worker_final_message="Manual oracle generation run",
        )
        console.print_json(_json.dumps(oracle_obj.to_json(), indent=2))
    except Exception as e:
        console.print(f"  [red]Oracle generation error:[/] {e}")


@main.command()
@click.argument("task_id", required=False)
def review(task_id: str | None) -> None:
    """Send the current Oracle to frontier reviewer(s).

    Dispatches the Core Oracle to the configured frontier reviewer
    and waits for a verdict. On FAIL, returns structured TODO items.

    See: FORGE_ARCHITECTURE_v0.2.md §5.3
    """
    console.print("[bold green]FORGE[/] Review")
    console.print("  Note: Frontier review requires ANTHROPIC_API_KEY.")
    console.print("  For bootstrap testing, review happens inside forge task loop.")
    console.print("  Standalone review: Phase 2+ feature.")


# ---------------------------------------------------------------------------
# Monitoring & Measurement
# ---------------------------------------------------------------------------


@main.command()
@click.option(
    "--period",
    type=click.Choice(["7d", "30d", "all"]),
    default="7d",
    help="Time window for boundary report.",
)
@click.option("--by-type", is_flag=True, help="Group by difficulty class.")
@click.option("--by-worker", is_flag=True, help="Group by worker identity.")
def boundary(period: str, by_type: bool, by_worker: bool) -> None:
    """Show frontier/local split report — the boundary dashboard.

    This is FORGE's core contribution: empirically tracking where
    local models suffice and where frontier judgment is required.

    See: FORGE_ARCHITECTURE_v0.2.md §7.3
    """
    from pathlib import Path

    from forge.boundary.measurement import BoundaryTracker

    tracker = BoundaryTracker(project_root=Path("."))
    report = tracker.generate_report(period=period, by_type=by_type, by_worker=by_worker)
    console.print(f"[bold green]FORGE[/] {report}")


@main.command()
def metrics() -> None:
    """Show frontier/local split, iteration counts, and cost data.

    See: FORGE_ARCHITECTURE_v0.2.md §10
    """
    from pathlib import Path

    from forge.observability.tracer import ForgeTracer

    db_path = Path(".forge/traces/forge.duckdb")
    if not db_path.exists():
        console.print("[bold green]FORGE[/] Metrics")
        console.print("  No trace data yet. Run forge task first.")
        return

    tracer = ForgeTracer(db_path=db_path)
    console.print("[bold green]FORGE[/] Metrics\n")

    try:
        result = tracer.query(
            "SELECT COUNT(*) as tasks, "
            "SUM(CASE WHEN first_pass_success THEN 1 ELSE 0 END) as passed, "
            "SUM(local_tokens) as local_tok, "
            "SUM(frontier_tokens_in + frontier_tokens_out) as frontier_tok "
            "FROM boundary_records"
        )
        if result["rows"]:
            row = result["rows"][0]
            tasks, passed, local_tok, frontier_tok = row
            rate = passed / tasks if tasks else 0
            console.print(f"  Total tasks: {tasks}")
            console.print(f"  First-pass rate: {rate:.0%}")
            console.print(f"  Local tokens: {local_tok:,}")
            console.print(f"  Frontier tokens: {frontier_tok:,}")
    except Exception:
        console.print("  No boundary data available.")

    try:
        result = tracer.query(
            "SELECT tag, COUNT(*) as cnt FROM error_taxonomy "
            "GROUP BY tag ORDER BY cnt DESC LIMIT 5"
        )
        if result["rows"]:
            console.print("\n  Top error tags:")
            for row in result["rows"]:
                console.print(f"    {row[0]}: {row[1]}")
    except Exception:
        pass

    tracer.close()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@main.group()
def config() -> None:
    """Configure FORGE settings (models, gate, frontier, hooks).

    See: FORGE_ARCHITECTURE_v0.2.md §13
    """
    pass


@config.command("models")
def config_models() -> None:
    """Configure model assignments per role (worker, planner, reviewer).

    See: FORGE_ARCHITECTURE_v0.2.md §13.1 models section
    """
    # TODO: Read and display current model config
    # TODO: Allow interactive editing of model assignments
    console.print("[bold green]FORGE[/] Config: Models")
    console.print("Not yet implemented — see §13.1 for config schema.")


@config.command("gate")
def config_gate() -> None:
    """Configure gate policy and trust parameters.

    See: FORGE_ARCHITECTURE_v0.2.md §13.1 gate section
    """
    # TODO: Read and display gate config
    # TODO: Allow editing of max_iterations, recovery_threshold, etc.
    console.print("[bold green]FORGE[/] Config: Gate")
    console.print("Not yet implemented — see §13.1 for config schema.")


@config.command("frontier")
def config_frontier() -> None:
    """Configure frontier API keys and model preferences.

    API keys are stored as environment variable names, never plaintext.

    See: FORGE_ARCHITECTURE_v0.2.md §13.1 frontier section, §14
    """
    # TODO: Display frontier model config
    # TODO: Validate API key env vars are set
    console.print("[bold green]FORGE[/] Config: Frontier")
    console.print("Not yet implemented — see §13.1 for config schema.")


@config.command("hooks")
def config_hooks() -> None:
    """Show/edit mechanical hooks configuration.

    See: FORGE_ARCHITECTURE_v0.2.md §6.1
    """
    # TODO: Read and display .forge/hooks.yaml
    # TODO: Allow interactive editing of hook rules
    console.print("[bold green]FORGE[/] Config: Hooks")
    console.print("Not yet implemented — see §6.1 for hooks spec.")


# ---------------------------------------------------------------------------
# Intervention
# ---------------------------------------------------------------------------


@main.command()
def intervene() -> None:
    """Pause execution and enter human PM mode (stub).

    Stops the current task/mission execution loop and presents
    the human with current state for direct intervention.

    See: FORGE_ARCHITECTURE_v0.2.md §2.1
    """
    # TODO: Pause orchestrator loop
    # TODO: Display current state and available actions
    # TODO: Accept human commands (approve, reject, replan, abort)
    console.print("[bold green]FORGE[/] Intervene")
    console.print("Not yet implemented — see §2.1 for intervention spec.")


@main.command()
@click.argument("task_id", required=False)
def approve(task_id: str | None) -> None:
    """Manually approve a pending gate / shadow-merge commit.

    In shadow mode, every PASS verdict still requires human approval
    before merging. This command approves the pending merge.

    See: FORGE_ARCHITECTURE_v0.2.md §5.5
    """
    # TODO: Find pending shadow-mode merge
    # TODO: Record approval in shadow-log.jsonl
    # TODO: Execute merge to main branch
    console.print("[bold green]FORGE[/] Approve")
    if task_id:
        console.print(f"  Approving task: {task_id}")
    console.print("Not yet implemented — see §5.5 for shadow mode spec.")


@main.command()
@click.argument("task_id", required=False)
@click.argument("reason", required=False, default="")
def reject(task_id: str | None, reason: str) -> None:
    """Reject a pending commit with specific feedback.

    The rejection reason is logged as a training signal and
    fed back to the worker for iteration.

    See: FORGE_ARCHITECTURE_v0.2.md §5.5
    """
    # TODO: Record rejection in shadow-log.jsonl
    # TODO: Feed reason back to worker as structured TODO
    console.print("[bold green]FORGE[/] Reject")
    if task_id:
        console.print(f"  Rejecting task: {task_id}")
    if reason:
        console.print(f"  Reason: {reason}")
    console.print("Not yet implemented — see §5.5 for shadow mode spec.")


@main.command()
def replan() -> None:
    """Trigger re-decomposition of current milestone.

    Sends the current milestone state back to the planner for
    re-decomposition. Used when the original plan is no longer viable.

    See: FORGE_ARCHITECTURE_v0.2.md §2.1
    """
    # TODO: Load current milestone state
    # TODO: Send to planner for re-decomposition
    # TODO: Update state.json with new task list
    console.print("[bold green]FORGE[/] Replan")
    console.print("Not yet implemented — see §3 for orchestrator spec.")


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------


@main.group()
def benchmark() -> None:
    """Benchmark cartridge system for controlled harness comparison.

    Run fixed task suites to compare harness configurations
    (new model, new LoRA, new Oracle format, new gate policy).

    See: FORGE_ARCHITECTURE_v0.2.md §8
    """
    pass


@benchmark.command("run")
@click.option("--cartridge", default=None, help="Run a single cartridge by name.")
@click.option("--tag", default=None, help="Label this run for comparison.")
def benchmark_run(cartridge: str | None, tag: str | None) -> None:
    """Execute the full benchmark cartridge suite (or a single cartridge).

    See: FORGE_ARCHITECTURE_v0.2.md §8
    """
    from pathlib import Path

    from forge.benchmark.runner import BenchmarkRunner

    runner = BenchmarkRunner(project_root=Path("."))
    run = runner.run(tag=tag or "default", cartridge_filter=cartridge)
    console.print(f"[bold green]FORGE[/] {run.summary()}")


@benchmark.command("compare")
@click.argument("tag1")
@click.argument("tag2")
def benchmark_compare(tag1: str, tag2: str) -> None:
    """Compare two benchmark runs by tag.

    See: FORGE_ARCHITECTURE_v0.2.md §8.3
    """
    from pathlib import Path

    from forge.benchmark.runner import BenchmarkRunner

    runner = BenchmarkRunner(project_root=Path("."))
    report = runner.compare(tag1, tag2)
    console.print(f"[bold green]FORGE[/] {report}")


@benchmark.command("list")
def benchmark_list() -> None:
    """List available benchmark cartridges.

    See: FORGE_ARCHITECTURE_v0.2.md §8.2
    """
    from pathlib import Path

    from forge.benchmark.runner import BenchmarkRunner

    runner = BenchmarkRunner(project_root=Path("."))
    carts = runner.list_cartridges()
    console.print("[bold green]FORGE[/] Benchmark Cartridges:")
    if not carts:
        console.print("  No cartridges found in .forge/benchmarks/")
    for c in carts:
        console.print(f"  {c['id']}: {c.get('name', '')} [{c.get('difficulty_class', '')}]")


# ---------------------------------------------------------------------------
# Observability extras
# ---------------------------------------------------------------------------


@main.command()
@click.option("--task", "task_id", default=None, help="Filter to specific task.")
@click.option("--full", is_flag=True, help="Include full Oracle + verdict payloads.")
def log(task_id: str | None, full: bool) -> None:
    """Show recent trace history (last 20 events).

    Queries the DuckDB trace database for recent spans.

    See: FORGE_ARCHITECTURE_v0.2.md §2.1, §10
    """
    # TODO: Query spans table for recent events
    # TODO: Filter by task_id if provided
    # TODO: Include Oracle/verdict payloads if --full
    console.print("[bold green]FORGE[/] Log")
    console.print("Not yet implemented — see §10 for observability spec.")


@main.command()
@click.argument("span_id")
def trace(span_id: str) -> None:
    """Inspect a specific trace span.

    See: FORGE_ARCHITECTURE_v0.2.md §10
    """
    # TODO: Query span by ID from DuckDB
    # TODO: Display span details with attributes
    console.print(f"[bold green]FORGE[/] Trace: {span_id}")
    console.print("Not yet implemented — see §10 for observability spec.")


@main.command()
def taxonomy() -> None:
    """Show error taxonomy distribution and trends.

    See: FORGE_ARCHITECTURE_v0.2.md §7.4
    """
    from pathlib import Path

    from forge.boundary.measurement import BoundaryTracker

    tracker = BoundaryTracker(project_root=Path("."))
    report = tracker.generate_taxonomy()
    console.print(f"[bold green]FORGE[/] {report}")


@main.command()
def digest() -> None:
    """Generate daily digest summary.

    Produces a Markdown summary of the day's work: tasks completed,
    boundary data, error distribution, cost, anomalies, skill events,
    and pending shadow-mode merges.

    See: FORGE_ARCHITECTURE_v0.2.md §10.4
    """
    # TODO: Query DuckDB for day's data
    # TODO: Generate Markdown digest
    # TODO: Write to .forge/digests/YYYY-MM-DD.md
    console.print("[bold green]FORGE[/] Daily Digest")
    console.print("Not yet implemented — see §10.4 for digest spec.")


@main.command()
def dashboard() -> None:
    """TUI: live progress, quality trends, model usage.

    Phase 1: Minimal text summary.
    Phase 2+: Full Textual TUI with live updates.

    See: FORGE_ARCHITECTURE_v0.2.md §2.1
    """
    # TODO: Phase 1: Display text summary of status + metrics
    # TODO: Phase 2+: Launch Textual TUI app
    console.print("[bold green]FORGE[/] Dashboard")
    console.print("Not yet implemented — Phase 1 text summary, Phase 2+ Textual TUI.")


# ---------------------------------------------------------------------------
# Skills & Learning
# ---------------------------------------------------------------------------


@main.group()
def skills() -> None:
    """Skill crystallization pipeline — learned patterns by tier.

    See: FORGE_ARCHITECTURE_v0.2.md §9
    """
    pass


@skills.command("list")
def skills_list() -> None:
    """List learned patterns/skills by tier.

    See: FORGE_ARCHITECTURE_v0.2.md §9
    """
    # TODO: Load skills from .forge/skills/
    # TODO: Display by tier with confidence and application counts
    console.print("[bold green]FORGE[/] Skills: List")
    console.print("Not yet implemented — see §9 for skill crystallization spec.")


@skills.command("promote")
@click.argument("skill_id")
def skills_promote(skill_id: str) -> None:
    """Manually promote a skill to the next tier.

    See: FORGE_ARCHITECTURE_v0.2.md §9.3
    """
    # TODO: Load skill by ID
    # TODO: Validate promotion requirements
    # TODO: Execute promotion logic
    console.print(f"[bold green]FORGE[/] Skills: Promote {skill_id}")
    console.print("Not yet implemented — see §9.3 for promotion logic.")


@main.command("export-training")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["preference-pairs", "sft", "both"]),
    default="both",
    help="Training data format.",
)
@click.option("--output", "output_path", default=None, help="Output path.")
def export_training(output_format: str, output_path: str | None) -> None:
    """Export accumulated data for LoRA fine-tuning (Phase 2+).

    See: FORGE_ARCHITECTURE_v0.2.md §9
    """
    # TODO: Collect training data from traces, verdicts, boundary records
    # TODO: Format as preference pairs or SFT examples
    # TODO: Write to output path
    console.print(f"[bold green]FORGE[/] Export Training — format: {output_format}")
    console.print("Not yet implemented — Phase 2+ feature.")


if __name__ == "__main__":
    main()

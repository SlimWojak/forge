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
    plan → execute → oracle → review → verdict → iterate/commit.

    Difficulty is classified by the planner model unless overridden
    with --difficulty.

    See: FORGE_ARCHITECTURE_v0.2.md §2.1, §3
    """
    # TODO: Create task in state.json
    # TODO: Classify difficulty (planner or manual override)
    # TODO: Create worktree for task (§12.2)
    # TODO: Enter orchestrator single-task loop (§3)
    console.print(f"[bold green]FORGE[/] Task: {description}")
    if difficulty:
        console.print(f"  Difficulty override: {difficulty}")
    console.print("Not yet implemented — see §3 for orchestrator spec.")


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

    Reads .forge/state.json and displays a human-readable summary
    of the current mission, task states, quality scores, and
    iteration counts.

    See: FORGE_ARCHITECTURE_v0.2.md §2.1, §3.2
    """
    # TODO: Read .forge/state.json
    # TODO: Display mission/task state table
    # TODO: Show quality scores and iteration counts
    # TODO: Show pending shadow-mode merges
    console.print("[bold green]FORGE[/] Status")
    console.print("Not yet implemented — see §3.2 for state schema.")


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
    # TODO: Run DesloppifyMechanical on changed files (§6.3)
    # TODO: If not mechanical_only, run DesloppifySubjective (§6.4)
    # TODO: Display score, delta, and issue list
    console.print("[bold green]FORGE[/] Quality scan")
    if mechanical_only:
        console.print("  Mode: mechanical only (tree-sitter)")
    else:
        console.print("  Mode: mechanical + subjective (LLM)")
    console.print("Not yet implemented — see §6.3-§6.4 for Desloppify spec.")


@main.command()
@click.argument("task_id", required=False)
def oracle(task_id: str | None) -> None:
    """Generate or display the Oracle snapshot for a task.

    The Oracle is a structured 2-4K token snapshot that mediates
    between local workers and frontier reviewers. Frontier models
    never see the full codebase — they see the Oracle.

    See: FORGE_ARCHITECTURE_v0.2.md §4
    """
    # TODO: If task_id given, display existing Oracle
    # TODO: If no task_id, generate Oracle for current task
    # TODO: Run Oracle pipeline: diff → codemap → checks → assemble (§4.4)
    console.print("[bold green]FORGE[/] Oracle")
    if task_id:
        console.print(f"  Displaying Oracle for task: {task_id}")
    else:
        console.print("  Generating Oracle for current task...")
    console.print("Not yet implemented — see §4 for Oracle spec.")


@main.command()
@click.argument("task_id", required=False)
def review(task_id: str | None) -> None:
    """Send the current Oracle to frontier reviewer(s).

    Dispatches the Core Oracle to the configured frontier reviewer
    and waits for a verdict. On FAIL, returns structured TODO items.

    See: FORGE_ARCHITECTURE_v0.2.md §5.3
    """
    # TODO: Load Oracle for task (§4)
    # TODO: Send to frontier reviewer via Gate Engine (§5.3)
    # TODO: Display verdict and TODO items if FAIL
    console.print("[bold green]FORGE[/] Review")
    if task_id:
        console.print(f"  Reviewing task: {task_id}")
    else:
        console.print("  Reviewing current task...")
    console.print("Not yet implemented — see §5.3 for gate flow spec.")


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
    # TODO: Query boundary_records from DuckDB (§7.2)
    # TODO: Compute first-pass success rates by difficulty class
    # TODO: Show boundary movement trends
    # TODO: Show cost summary
    console.print(f"[bold green]FORGE[/] Boundary Report — period: {period}")
    console.print("Not yet implemented — see §7.3 for output format.")


@main.command()
def metrics() -> None:
    """Show frontier/local split, iteration counts, and cost data.

    Queries the DuckDB observability database for aggregated metrics
    across all completed tasks.

    See: FORGE_ARCHITECTURE_v0.2.md §10
    """
    # TODO: Query DuckDB for aggregated metrics
    # TODO: Display frontier/local token split
    # TODO: Display cost breakdown by provider
    console.print("[bold green]FORGE[/] Metrics")
    console.print("Not yet implemented — see §10 for observability spec.")


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
    # TODO: Load cartridge-manifest.yaml
    # TODO: Execute cartridges in isolated worktrees
    # TODO: Collect results and write to benchmark-results/
    console.print("[bold green]FORGE[/] Benchmark: Run")
    if cartridge:
        console.print(f"  Cartridge: {cartridge}")
    if tag:
        console.print(f"  Tag: {tag}")
    console.print("Not yet implemented — see §8 for benchmark spec.")


@benchmark.command("compare")
@click.argument("tag1")
@click.argument("tag2")
def benchmark_compare(tag1: str, tag2: str) -> None:
    """Compare two benchmark runs by tag.

    See: FORGE_ARCHITECTURE_v0.2.md §8.3
    """
    # TODO: Load benchmark results by tag
    # TODO: Compute deltas across cartridge results
    # TODO: Display comparison table
    console.print(f"[bold green]FORGE[/] Benchmark: Compare {tag1} vs {tag2}")
    console.print("Not yet implemented — see §8.3 for results schema.")


@benchmark.command("list")
def benchmark_list() -> None:
    """List available benchmark cartridges.

    See: FORGE_ARCHITECTURE_v0.2.md §8.2
    """
    # TODO: Load cartridge-manifest.yaml
    # TODO: Display cartridge list with difficulty classes
    console.print("[bold green]FORGE[/] Benchmark: List")
    console.print("Not yet implemented — see §8.2 for cartridge spec.")


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
    # TODO: Query error_taxonomy table from DuckDB
    # TODO: Compute distribution percentages
    # TODO: Show trends vs previous period
    console.print("[bold green]FORGE[/] Error Taxonomy")
    console.print("Not yet implemented — see §7.4 for taxonomy spec.")


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

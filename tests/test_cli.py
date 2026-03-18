"""Tests for FORGE CLI — verify the CLI loads and --help works.

These are basic smoke tests to ensure the scaffold is importable
and the Click CLI is correctly wired.
"""

from __future__ import annotations

from click.testing import CliRunner

from forge import __version__
from forge.cli import main


def test_version() -> None:
    """Verify the package version is set."""
    assert __version__ == "0.2.0"


def test_cli_help() -> None:
    """Verify 'forge --help' runs without error."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "FORGE" in result.output
    assert "frontier/local" in result.output.lower() or "forge" in result.output.lower()


def test_cli_version() -> None:
    """Verify 'forge --version' shows the correct version."""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.2.0" in result.output


def test_init_help() -> None:
    """Verify 'forge init --help' runs."""
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--help"])
    assert result.exit_code == 0
    assert "Scaffold" in result.output or "project" in result.output.lower()


def test_task_help() -> None:
    """Verify 'forge task --help' runs."""
    runner = CliRunner()
    result = runner.invoke(main, ["task", "--help"])
    assert result.exit_code == 0
    assert "--difficulty" in result.output


def test_mission_help() -> None:
    """Verify 'forge mission --help' runs."""
    runner = CliRunner()
    result = runner.invoke(main, ["mission", "--help"])
    assert result.exit_code == 0
    assert "--mode" in result.output


def test_status_help() -> None:
    """Verify 'forge status --help' runs."""
    runner = CliRunner()
    result = runner.invoke(main, ["status", "--help"])
    assert result.exit_code == 0


def test_quality_help() -> None:
    """Verify 'forge quality --help' runs."""
    runner = CliRunner()
    result = runner.invoke(main, ["quality", "--help"])
    assert result.exit_code == 0
    assert "--mechanical-only" in result.output


def test_oracle_help() -> None:
    """Verify 'forge oracle --help' runs."""
    runner = CliRunner()
    result = runner.invoke(main, ["oracle", "--help"])
    assert result.exit_code == 0


def test_review_help() -> None:
    """Verify 'forge review --help' runs."""
    runner = CliRunner()
    result = runner.invoke(main, ["review", "--help"])
    assert result.exit_code == 0


def test_boundary_help() -> None:
    """Verify 'forge boundary --help' runs."""
    runner = CliRunner()
    result = runner.invoke(main, ["boundary", "--help"])
    assert result.exit_code == 0
    assert "--period" in result.output


def test_metrics_help() -> None:
    """Verify 'forge metrics --help' runs."""
    runner = CliRunner()
    result = runner.invoke(main, ["metrics", "--help"])
    assert result.exit_code == 0


def test_config_help() -> None:
    """Verify 'forge config --help' shows subcommands."""
    runner = CliRunner()
    result = runner.invoke(main, ["config", "--help"])
    assert result.exit_code == 0
    assert "models" in result.output
    assert "gate" in result.output
    assert "frontier" in result.output
    assert "hooks" in result.output


def test_benchmark_help() -> None:
    """Verify 'forge benchmark --help' shows subcommands."""
    runner = CliRunner()
    result = runner.invoke(main, ["benchmark", "--help"])
    assert result.exit_code == 0
    assert "run" in result.output
    assert "compare" in result.output
    assert "list" in result.output


def test_skills_help() -> None:
    """Verify 'forge skills --help' shows subcommands."""
    runner = CliRunner()
    result = runner.invoke(main, ["skills", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "promote" in result.output


def test_intervene_help() -> None:
    """Verify 'forge intervene --help' runs."""
    runner = CliRunner()
    result = runner.invoke(main, ["intervene", "--help"])
    assert result.exit_code == 0


def test_taxonomy_help() -> None:
    """Verify 'forge taxonomy --help' runs."""
    runner = CliRunner()
    result = runner.invoke(main, ["taxonomy", "--help"])
    assert result.exit_code == 0


def test_digest_help() -> None:
    """Verify 'forge digest --help' runs."""
    runner = CliRunner()
    result = runner.invoke(main, ["digest", "--help"])
    assert result.exit_code == 0


def test_init_command() -> None:
    """Verify 'forge init' runs (stub output)."""
    runner = CliRunner()
    result = runner.invoke(main, ["init", "my-project"])
    assert result.exit_code == 0
    assert "my-project" in result.output


def test_task_command() -> None:
    """Verify 'forge task' runs (stub output)."""
    runner = CliRunner()
    result = runner.invoke(main, ["task", "Implement login"])
    assert result.exit_code == 0
    assert "Implement login" in result.output


def test_task_with_difficulty() -> None:
    """Verify 'forge task --difficulty' accepts valid values."""
    runner = CliRunner()
    result = runner.invoke(
        main, ["task", "Fix types", "--difficulty", "mechanical"]
    )
    assert result.exit_code == 0
    assert "mechanical" in result.output


def test_status_command() -> None:
    """Verify 'forge status' runs (stub output)."""
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    assert result.exit_code == 0


def test_quality_command() -> None:
    """Verify 'forge quality' runs (stub output)."""
    runner = CliRunner()
    result = runner.invoke(main, ["quality"])
    assert result.exit_code == 0


def test_boundary_command() -> None:
    """Verify 'forge boundary' runs (stub output)."""
    runner = CliRunner()
    result = runner.invoke(main, ["boundary"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Import smoke tests — verify all modules are importable
# ---------------------------------------------------------------------------


def test_import_forge() -> None:
    """Verify the forge package is importable."""
    import forge

    assert forge.__version__


def test_import_aci() -> None:
    """Verify the ACI module is importable."""
    from forge.aci import Tool, ToolResult, ViewResult, EditResult
    from forge.aci.tools import view_file, edit_file, search_file, run_command, run_tests

    assert Tool is not None
    assert ToolResult is not None


def test_import_oracle() -> None:
    """Verify the Oracle module is importable."""
    from forge.oracle import CoreOracle, OracleGenerator, DiffSummary

    assert CoreOracle is not None
    assert OracleGenerator is not None


def test_import_gate() -> None:
    """Verify the Gate module is importable."""
    from forge.gate import GateEngine, Verdict, DifficultyClass, VerdictOutcome

    assert GateEngine is not None
    assert DifficultyClass.MECHANICAL.value == "mechanical"


def test_import_orchestrator() -> None:
    """Verify the Orchestrator module is importable."""
    from forge.orchestrator import MissionControl, TaskState, RecoveryDecision

    assert MissionControl is not None
    assert TaskState.INIT.value == "init"


def test_import_enforcement() -> None:
    """Verify the Enforcement module is importable."""
    from forge.enforcement import (
        HookRunner,
        ArchitecturalLinter,
        DesloppifyMechanical,
        DesloppifySubjective,
    )

    assert HookRunner is not None


def test_import_observability() -> None:
    """Verify the Observability module is importable."""
    from forge.observability import ForgeTracer

    assert ForgeTracer is not None


def test_import_models() -> None:
    """Verify the Models module is importable."""
    from forge.models import ModelProvider, ModelRole

    assert ModelProvider is not None
    assert ModelRole.WORKER.value == "worker"


def test_import_boundary() -> None:
    """Verify the Boundary module is importable."""
    from forge.boundary import BoundaryRecord, BoundaryTracker, ErrorTaxonomy

    assert BoundaryTracker is not None
    assert ErrorTaxonomy.MISSING_TESTS.value == "missing-tests"


def test_import_skills() -> None:
    """Verify the Skills module is importable."""
    from forge.skills import Skill, SkillManager, SkillTier

    assert SkillManager is not None
    assert SkillTier.PROMPT == 1

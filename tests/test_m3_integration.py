"""Integration tests for M3: F014 (Benchmark), F016 (forge task E2E), F017 (status/metrics)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from forge.benchmark.runner import BenchmarkRun, BenchmarkRunner, load_cartridges
from forge.cli import main

# ---------------------------------------------------------------------------
# F014: Benchmark Cartridge Runner
# ---------------------------------------------------------------------------


@pytest.fixture()
def benchmark_project(tmp_path: Path) -> Path:
    """Create a project with a benchmark cartridge."""
    bench_dir = tmp_path / ".forge" / "benchmarks"
    bench_dir.mkdir(parents=True)
    (tmp_path / ".forge" / "benchmark-results").mkdir(parents=True)

    cart = {
        "id": "test-cart-01",
        "name": "Add greeting function",
        "description": "Add a hello() function to app.py",
        "difficulty_class": "mechanical",
        "category": "add-function",
        "timeout_seconds": 60,
        "max_iterations": 3,
        "success_criteria": {"mechanical_checks": {"tests": "must_pass"}},
    }
    import yaml
    (bench_dir / "test-cart-01.yaml").write_text(yaml.dump(cart))

    return tmp_path


class TestBenchmarkRunner:
    """test_benchmark_runner — cartridge execution and storage."""

    def test_load_cartridges(self, benchmark_project: Path) -> None:
        carts = load_cartridges(benchmark_project / ".forge" / "benchmarks")
        assert len(carts) == 1
        assert carts[0]["id"] == "test-cart-01"

    def test_run_produces_results(self, benchmark_project: Path) -> None:
        runner = BenchmarkRunner(project_root=benchmark_project)
        run = runner.run(tag="test-baseline")
        assert isinstance(run, BenchmarkRun)
        assert run.tag == "test-baseline"
        assert run.total == 1

    def test_results_stored_on_disk(self, benchmark_project: Path) -> None:
        runner = BenchmarkRunner(project_root=benchmark_project)
        runner.run(tag="test-baseline")
        result_files = list(
            (benchmark_project / ".forge" / "benchmark-results").glob("*.json")
        )
        assert len(result_files) >= 1

    def test_summary_output(self, benchmark_project: Path) -> None:
        runner = BenchmarkRunner(project_root=benchmark_project)
        run = runner.run(tag="test-run")
        summary = run.summary()
        assert "test-run" in summary
        assert "test-cart-01" in summary

    def test_compare_runs(self, benchmark_project: Path) -> None:
        runner = BenchmarkRunner(project_root=benchmark_project)
        runner.run(tag="baseline")
        runner.run(tag="new-model")
        report = runner.compare("baseline", "new-model")
        assert "baseline" in report
        assert "new-model" in report


# ---------------------------------------------------------------------------
# F016: forge task CLI (E2E integration test with mock models)
# ---------------------------------------------------------------------------


class TestForgeTaskE2E:
    """test_forge_task_e2e — forge task command runs."""

    def test_task_command_accepts_description(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["task", "Implement login"])
        assert result.exit_code == 0
        assert "Implement login" in result.output

    def test_task_with_difficulty_override(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main, ["task", "Fix types", "--difficulty", "mechanical"]
        )
        assert result.exit_code == 0
        assert "mechanical" in result.output


# ---------------------------------------------------------------------------
# F017: forge status and forge metrics
# ---------------------------------------------------------------------------


class TestForgeStatus:
    """test_status_command — forge status shows state."""

    def test_status_runs(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "FORGE" in result.output

    def test_status_shows_feature_progress(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create feature_list.json
            features = {
                "phase_1": {
                    "milestone_1": {
                        "name": "Test MS",
                        "features": [
                            {"id": "F001", "passes": True},
                            {"id": "F002", "passes": False},
                        ],
                    }
                }
            }
            Path("feature_list.json").write_text(json.dumps(features))
            result = runner.invoke(main, ["status"])
            assert "1/2" in result.output


class TestForgeMetrics:
    """test_metrics_command — forge metrics displays data."""

    def test_metrics_runs_without_db(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["metrics"])
        assert result.exit_code == 0

    def test_metrics_with_data(self, tmp_path: Path) -> None:
        from forge.observability.tracer import ForgeTracer

        db_path = tmp_path / ".forge" / "traces" / "forge.duckdb"
        tracer = ForgeTracer(db_path=db_path)
        tracer.initialize_schema()
        tracer.record_boundary(
            task_id="t-1", mission_id="m1", mission_mode="delivery",
            difficulty_class="local-reasoning", worker_model="qwen",
            first_pass_success=True, total_iterations=1,
            local_tokens=5000, frontier_tokens_in=2000,
            frontier_tokens_out=500, wall_clock_seconds=30,
        )
        tracer.close()

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Symlink the .forge dir
            Path(".forge").symlink_to(tmp_path / ".forge")
            result = runner.invoke(main, ["metrics"])
            assert result.exit_code == 0
            # Should show some data
            assert "1" in result.output or "task" in result.output.lower()

"""Tests for FORGE Oracle Generator (F008).

Uses real git repos with fixtures to test the Oracle pipeline.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from forge.oracle.generator import (
    CoreOracle,
    DiffSummary,
    OracleGenerator,
    TaskContext,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def git_project(tmp_path: Path) -> Path:
    """Create a git repo with an initial commit and a change to diff."""
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init"], cwd=str(project), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@forge.dev"],
        cwd=str(project), capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(project), capture_output=True,
    )

    # Initial commit on main
    src = project / "src"
    src.mkdir()
    (src / "app.py").write_text(
        'def hello():\n    return "hello"\n\nx = 1\n'
    )
    (project / "tests").mkdir()
    (project / "tests" / "test_app.py").write_text(
        "def test_placeholder():\n    assert True\n"
    )
    subprocess.run(["git", "add", "."], cwd=str(project), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=str(project), capture_output=True,
    )

    # Make a change (on the same branch for simplicity)
    (src / "app.py").write_text(
        'def hello(name: str) -> str:\n'
        '    return f"hello {name}"\n\n'
        'def goodbye() -> str:\n'
        '    return "bye"\n\n'
        'x = 1\n'
    )
    (src / "utils.py").write_text(
        'def helper():\n    return 42\n'
    )
    subprocess.run(["git", "add", "."], cwd=str(project), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add features"],
        cwd=str(project), capture_output=True,
    )

    return project


@pytest.fixture()
def oracle_gen(git_project: Path) -> OracleGenerator:
    """Create an OracleGenerator pointing at the test project."""
    forge_dir = git_project / ".forge"
    forge_dir.mkdir(exist_ok=True)
    return OracleGenerator(project_root=git_project)


# ---------------------------------------------------------------------------
# F008: Oracle Generator
# ---------------------------------------------------------------------------


class TestOracleGeneration:
    """test_oracle_generation — full pipeline with real diff fixture."""

    def test_build_oracle_returns_core_oracle(
        self, oracle_gen: OracleGenerator, git_project: Path
    ) -> None:
        oracle = oracle_gen.build_oracle(
            task_id="001",
            worktree_path=git_project,
            main_branch="HEAD~1",
        )
        assert isinstance(oracle, CoreOracle)
        assert oracle.oracle_id == "oracle-001-iter-1"
        assert oracle.oracle_version == "0.2"

    def test_diff_summary_populated(
        self, oracle_gen: OracleGenerator, git_project: Path
    ) -> None:
        oracle = oracle_gen.build_oracle(
            task_id="001",
            worktree_path=git_project,
            main_branch="HEAD~1",
        )
        assert oracle.diff_summary is not None
        assert oracle.diff_summary.files_changed >= 1
        assert oracle.diff_summary.insertions > 0

    def test_codemap_has_changed_files(
        self, oracle_gen: OracleGenerator, git_project: Path
    ) -> None:
        oracle = oracle_gen.build_oracle(
            task_id="001",
            worktree_path=git_project,
            main_branch="HEAD~1",
        )
        assert oracle.codemap is not None
        assert len(oracle.codemap.changed_files) >= 1
        paths = [f.path for f in oracle.codemap.changed_files]
        assert any("app.py" in p for p in paths)

    def test_codemap_has_signatures(
        self, oracle_gen: OracleGenerator, git_project: Path
    ) -> None:
        oracle = oracle_gen.build_oracle(
            task_id="001",
            worktree_path=git_project,
            main_branch="HEAD~1",
        )
        all_sigs = []
        for f in oracle.codemap.changed_files:
            all_sigs.extend(f.signatures)
        assert len(all_sigs) > 0

    def test_mechanical_checks_present(
        self, oracle_gen: OracleGenerator, git_project: Path
    ) -> None:
        oracle = oracle_gen.build_oracle(
            task_id="001",
            worktree_path=git_project,
            main_branch="HEAD~1",
        )
        assert oracle.mechanical_checks is not None
        assert oracle.mechanical_checks.tests is not None
        assert oracle.mechanical_checks.tests.status in ("pass", "fail")

    def test_worker_self_assessment_default(
        self, oracle_gen: OracleGenerator, git_project: Path
    ) -> None:
        oracle = oracle_gen.build_oracle(
            task_id="001",
            worktree_path=git_project,
            main_branch="HEAD~1",
            worker_final_message="I finished the task.",
        )
        assert oracle.worker_self_assessment is not None
        assert oracle.worker_self_assessment.confidence == "medium"

    def test_worker_self_assessment_parsed(
        self, oracle_gen: OracleGenerator, git_project: Path
    ) -> None:
        msg = (
            'Done. Here is my assessment: '
            '{"confidence": "high", "concerns": ["no tests"], '
            '"decisions_made": ["used dataclass"]}'
        )
        oracle = oracle_gen.build_oracle(
            task_id="001",
            worktree_path=git_project,
            main_branch="HEAD~1",
            worker_final_message=msg,
        )
        assert oracle.worker_self_assessment.confidence == "high"
        assert "no tests" in oracle.worker_self_assessment.concerns

    def test_task_context_passed_through(
        self, oracle_gen: OracleGenerator, git_project: Path
    ) -> None:
        ctx = TaskContext(
            mission="test mission",
            milestone="m1",
            milestone_description="first milestone",
            task_id="001",
            task_description="add features",
            difficulty_class="local-reasoning",
            mission_mode="delivery",
            feature_list_progress="1/5",
            milestone_progress="1/3",
            iteration=1,
            total_iterations_this_task=1,
        )
        oracle = oracle_gen.build_oracle(
            task_id="001",
            worktree_path=git_project,
            main_branch="HEAD~1",
            task_context=ctx,
        )
        assert oracle.task_context is not None
        assert oracle.task_context.task_id == "001"

    def test_oracle_persisted_to_disk(
        self, oracle_gen: OracleGenerator, git_project: Path
    ) -> None:
        oracle = oracle_gen.build_oracle(
            task_id="002",
            worktree_path=git_project,
            main_branch="HEAD~1",
        )
        oracle_dir = git_project / ".forge" / "oracles" / oracle.oracle_id
        assert (oracle_dir / "core.json").exists()
        assert (oracle_dir / "metadata.json").exists()

        core_data = json.loads((oracle_dir / "core.json").read_text())
        assert core_data["$schema"] == "forge-oracle-v0.2"
        assert core_data["oracle_id"] == oracle.oracle_id


class TestOracleToJson:
    """CoreOracle serialization and deserialization."""

    def test_to_json_has_schema(self) -> None:
        oracle = CoreOracle(oracle_id="test-001", timestamp="2026-01-01T00:00:00Z")
        data = oracle.to_json()
        assert data["$schema"] == "forge-oracle-v0.2"
        assert data["oracle_version"] == "0.2"

    def test_to_json_includes_diff_summary(self) -> None:
        oracle = CoreOracle(
            oracle_id="test-001",
            diff_summary=DiffSummary(
                files_changed=2, files_added=1, files_deleted=0,
                insertions=50, deletions=10,
            ),
        )
        data = oracle.to_json()
        assert data["diff_summary"]["files_changed"] == 2
        assert data["diff_summary"]["insertions"] == 50

    def test_round_trip_basic(self) -> None:
        oracle = CoreOracle(
            oracle_id="round-trip",
            timestamp="2026-01-01",
            available_annexes=["full_patch"],
        )
        data = oracle.to_json()
        restored = CoreOracle.from_json(data)
        assert restored.oracle_id == "round-trip"
        assert restored.available_annexes == ["full_patch"]


class TestAnnexStaging:
    """Annex files are staged to disk."""

    def test_full_patch_staged(
        self, oracle_gen: OracleGenerator, git_project: Path
    ) -> None:
        oracle = oracle_gen.build_oracle(
            task_id="003",
            worktree_path=git_project,
            main_branch="HEAD~1",
        )
        annex_dir = (
            git_project / ".forge" / "oracles" / oracle.oracle_id / "annexes"
        )
        if "full_patch" in oracle.available_annexes:
            assert (annex_dir / "full_patch.diff").exists()
            content = (annex_dir / "full_patch.diff").read_text()
            assert len(content) > 0


class TestOracleTokenBudget:
    """Oracle should target 2-4K tokens."""

    def test_core_oracle_token_estimate(
        self, oracle_gen: OracleGenerator, git_project: Path
    ) -> None:
        oracle = oracle_gen.build_oracle(
            task_id="004",
            worktree_path=git_project,
            main_branch="HEAD~1",
        )
        json_str = json.dumps(oracle.to_json())
        # Rough estimate: 1 token ~ 4 chars
        token_estimate = len(json_str) // 4
        # For a small test diff, should be well under 4K
        assert token_estimate < 8000, f"Oracle too large: ~{token_estimate} tokens"

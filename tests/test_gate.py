"""Tests for FORGE Gate Engine (F009).

Uses mock reviewer models to test the gate flow without
requiring real frontier API endpoints.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from forge.gate.engine import (
    DifficultyClass,
    GateEngine,
    ReviewerInfo,
    Verdict,
    VerdictIssue,
    VerdictOutcome,
    _parse_verdict_json,
)
from forge.oracle.generator import CoreOracle, DiffSummary

# ---------------------------------------------------------------------------
# Mock reviewer models
# ---------------------------------------------------------------------------


class MockPassReviewer:
    """A reviewer that always returns PASS."""

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
                        "summary": "Implementation looks good.",
                        "issues": [],
                    })
                }
            }]
        }


class MockFailReviewer:
    """A reviewer that always returns FAIL with structured issues."""

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
                        "summary": "Missing test coverage.",
                        "issues": [
                            {
                                "id": "issue-001",
                                "file": "src/app.py",
                                "line_range": [10, 20],
                                "severity": "blocking",
                                "category": "missing-tests",
                                "what": "No test for error case",
                                "why": "Error paths must be tested",
                                "fix": "Add test for 400 response",
                                "acceptance_criteria": "Test exists and passes",
                            }
                        ],
                    })
                }
            }]
        }


class MockErrorReviewer:
    """A reviewer that raises an exception."""

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        raise ConnectionError("API endpoint unavailable")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def gate_project(tmp_path: Path) -> Path:
    """Create a minimal project directory for gate engine."""
    forge_dir = tmp_path / ".forge"
    forge_dir.mkdir()
    (forge_dir / "verdicts").mkdir()
    return tmp_path


@pytest.fixture()
def sample_oracle() -> CoreOracle:
    """Create a minimal CoreOracle for testing."""
    return CoreOracle(
        oracle_id="oracle-001-iter-1",
        timestamp="2026-03-18T10:00:00Z",
        diff_summary=DiffSummary(
            files_changed=2, files_added=1, files_deleted=0,
            insertions=50, deletions=10,
        ),
    )


# ---------------------------------------------------------------------------
# F009: Gate Engine
# ---------------------------------------------------------------------------


class TestGatePass:
    """test_gate_pass — PASS verdict from reviewer."""

    def test_pass_verdict_returned(
        self, gate_project: Path, sample_oracle: CoreOracle
    ) -> None:
        engine = GateEngine(
            project_root=gate_project,
            reviewer=MockPassReviewer(),
        )
        verdict = engine.send_to_reviewer(sample_oracle, task_id="001")
        assert isinstance(verdict, Verdict)
        assert verdict.verdict == VerdictOutcome.PASS

    def test_pass_has_summary(
        self, gate_project: Path, sample_oracle: CoreOracle
    ) -> None:
        engine = GateEngine(
            project_root=gate_project,
            reviewer=MockPassReviewer(),
        )
        verdict = engine.send_to_reviewer(sample_oracle, task_id="001")
        assert verdict.summary != ""

    def test_pass_no_blocking_issues(
        self, gate_project: Path, sample_oracle: CoreOracle
    ) -> None:
        engine = GateEngine(
            project_root=gate_project,
            reviewer=MockPassReviewer(),
        )
        verdict = engine.send_to_reviewer(sample_oracle, task_id="001")
        blocking = [i for i in verdict.issues if i.severity == "blocking"]
        assert len(blocking) == 0

    def test_verdict_persisted_to_disk(
        self, gate_project: Path, sample_oracle: CoreOracle
    ) -> None:
        engine = GateEngine(
            project_root=gate_project,
            reviewer=MockPassReviewer(),
        )
        verdict = engine.send_to_reviewer(sample_oracle, task_id="001")
        verdict_file = gate_project / ".forge" / "verdicts" / f"{verdict.verdict_id}.json"
        assert verdict_file.exists()
        data = json.loads(verdict_file.read_text())
        assert data["verdict"] == "PASS"


class TestGateFail:
    """test_gate_fail — FAIL verdict with structured TODOs."""

    def test_fail_verdict_returned(
        self, gate_project: Path, sample_oracle: CoreOracle
    ) -> None:
        engine = GateEngine(
            project_root=gate_project,
            reviewer=MockFailReviewer(),
        )
        verdict = engine.send_to_reviewer(sample_oracle, task_id="001")
        assert verdict.verdict == VerdictOutcome.FAIL

    def test_fail_has_issues(
        self, gate_project: Path, sample_oracle: CoreOracle
    ) -> None:
        engine = GateEngine(
            project_root=gate_project,
            reviewer=MockFailReviewer(),
        )
        verdict = engine.send_to_reviewer(sample_oracle, task_id="001")
        assert len(verdict.issues) >= 1
        issue = verdict.issues[0]
        assert issue.severity == "blocking"
        assert issue.file == "src/app.py"
        assert issue.what != ""
        assert issue.fix != ""

    def test_fail_has_error_taxonomy_tags(
        self, gate_project: Path, sample_oracle: CoreOracle
    ) -> None:
        engine = GateEngine(
            project_root=gate_project,
            reviewer=MockFailReviewer(),
        )
        verdict = engine.send_to_reviewer(sample_oracle, task_id="001")
        assert "missing-tests" in verdict.error_taxonomy_tags

    def test_extract_todos_from_verdict(
        self, gate_project: Path, sample_oracle: CoreOracle
    ) -> None:
        engine = GateEngine(
            project_root=gate_project,
            reviewer=MockFailReviewer(),
        )
        verdict = engine.send_to_reviewer(sample_oracle, task_id="001")
        todos = engine.extract_todos_from_verdict(verdict)
        assert len(todos) >= 1
        assert "file" in todos[0]
        assert "fix" in todos[0]


class TestGateApiError:
    """test_gate_api_error — handles API errors gracefully."""

    def test_api_error_returns_fail_verdict(
        self, gate_project: Path, sample_oracle: CoreOracle
    ) -> None:
        engine = GateEngine(
            project_root=gate_project,
            reviewer=MockErrorReviewer(),
        )
        verdict = engine.send_to_reviewer(sample_oracle, task_id="001")
        assert verdict.verdict == VerdictOutcome.FAIL
        assert "API error" in verdict.summary

    def test_no_reviewer_raises(
        self, gate_project: Path, sample_oracle: CoreOracle
    ) -> None:
        engine = GateEngine(project_root=gate_project)
        with pytest.raises(RuntimeError, match="No reviewer model configured"):
            engine.send_to_reviewer(sample_oracle, task_id="001")


class TestGateEscalation:
    """Escalation to second reviewer on repeated failures."""

    def test_should_escalate_on_iteration_2(self, gate_project: Path) -> None:
        engine = GateEngine(project_root=gate_project)
        assert engine.should_escalate(1) is False
        assert engine.should_escalate(2) is True
        assert engine.should_escalate(3) is True

    def test_should_enter_recovery_on_iteration_3(
        self, gate_project: Path
    ) -> None:
        engine = GateEngine(project_root=gate_project)
        assert engine.should_enter_recovery(2) is False
        assert engine.should_enter_recovery(3) is True

    def test_escalation_uses_second_reviewer(
        self, gate_project: Path, sample_oracle: CoreOracle
    ) -> None:
        engine = GateEngine(
            project_root=gate_project,
            reviewer=MockFailReviewer(),
            escalation_reviewer=MockPassReviewer(),
        )
        verdict = engine.send_to_reviewer(sample_oracle, iteration=2, task_id="001")
        assert verdict.verdict == VerdictOutcome.PASS


class TestShadowMode:
    """Shadow mode proposal and human decision logging."""

    def test_propose_commit(
        self, gate_project: Path, sample_oracle: CoreOracle
    ) -> None:
        engine = GateEngine(
            project_root=gate_project,
            reviewer=MockPassReviewer(),
        )
        verdict = engine.send_to_reviewer(sample_oracle, task_id="001")
        proposal = engine.propose_commit("001", verdict)
        assert proposal["task_id"] == "001"
        assert proposal["verdict"] == "PASS"
        assert proposal["shadow_mode"] is True

    def test_shadow_log_written(
        self, gate_project: Path, sample_oracle: CoreOracle
    ) -> None:
        engine = GateEngine(
            project_root=gate_project,
            reviewer=MockPassReviewer(),
        )
        verdict = engine.send_to_reviewer(sample_oracle, task_id="001")
        engine.propose_commit("001", verdict)
        log_path = gate_project / ".forge" / "shadow-log.jsonl"
        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) >= 1
        event = json.loads(lines[0])
        assert event["shadow_event"]["task_id"] == "001"

    def test_record_human_decision(self, gate_project: Path) -> None:
        engine = GateEngine(project_root=gate_project)
        engine.record_human_decision("001", "oracle-001", "approved")
        log_path = gate_project / ".forge" / "shadow-log.jsonl"
        lines = log_path.read_text().strip().splitlines()
        event = json.loads(lines[-1])
        assert event["shadow_event"]["human_decision"] == "approved"


class TestDifficultyClassifier:
    """Difficulty classification heuristic."""

    def test_mechanical_classification(self, gate_project: Path) -> None:
        engine = GateEngine(project_root=gate_project)
        result = engine.difficulty_classifier("Fix lint errors in auth module")
        assert result.difficulty_class == DifficultyClass.MECHANICAL

    def test_local_reasoning_classification(self, gate_project: Path) -> None:
        engine = GateEngine(project_root=gate_project)
        result = engine.difficulty_classifier("Implement login endpoint")
        assert result.difficulty_class == DifficultyClass.LOCAL_REASONING

    def test_architectural_classification(self, gate_project: Path) -> None:
        engine = GateEngine(project_root=gate_project)
        result = engine.difficulty_classifier("Refactor the data layer architecture")
        assert result.difficulty_class == DifficultyClass.ARCHITECTURAL

    def test_uncertain_classification(self, gate_project: Path) -> None:
        engine = GateEngine(project_root=gate_project)
        result = engine.difficulty_classifier("Make it better somehow")
        assert result.difficulty_class == DifficultyClass.UNCERTAIN


class TestVerdictSerialization:
    """Verdict to_json and from_json."""

    def test_verdict_to_json(self) -> None:
        verdict = Verdict(
            verdict_id="v-001",
            oracle_id="o-001",
            task_id="t-001",
            timestamp="2026-01-01",
            reviewer=ReviewerInfo(
                model="sonnet-4.6", provider="anthropic",
                role="primary_reviewer",
            ),
            verdict=VerdictOutcome.PASS,
            summary="Looks good.",
        )
        data = verdict.to_json()
        assert data["$schema"] == "forge-verdict-v0.2"
        assert data["verdict"] == "PASS"

    def test_verdict_round_trip(self) -> None:
        original = Verdict(
            verdict_id="v-002",
            oracle_id="o-002",
            task_id="t-002",
            timestamp="2026-01-01",
            reviewer=ReviewerInfo(
                model="codex", provider="openai",
                role="escalation_reviewer",
            ),
            verdict=VerdictOutcome.FAIL,
            error_taxonomy_tags=["missing-tests"],
            summary="Missing tests.",
            issues=[
                VerdictIssue(
                    id="i-001", file="app.py", line_range=[1, 5],
                    severity="blocking", category="missing-tests",
                    what="No tests", why="Need coverage",
                    fix="Add tests", acceptance_criteria="Tests pass",
                )
            ],
        )
        data = original.to_json()
        restored = Verdict.from_json(data)
        assert restored.verdict == VerdictOutcome.FAIL
        assert len(restored.issues) == 1
        assert restored.issues[0].file == "app.py"


class TestParseVerdictJson:
    """_parse_verdict_json handles various response formats."""

    def test_clean_json(self) -> None:
        text = json.dumps({
            "verdict": "PASS", "summary": "OK",
            "error_taxonomy_tags": [], "issues": [],
        })
        reviewer = ReviewerInfo(model="test", provider="test", role="test")
        v = _parse_verdict_json(text, "o-1", "t-1", reviewer)
        assert v.verdict == VerdictOutcome.PASS

    def test_json_in_code_fence(self) -> None:
        text = '```json\n{"verdict": "FAIL", "summary": "Bad", "issues": []}\n```'
        reviewer = ReviewerInfo(model="test", provider="test", role="test")
        v = _parse_verdict_json(text, "o-1", "t-1", reviewer)
        assert v.verdict == VerdictOutcome.FAIL

    def test_no_json_fallback(self) -> None:
        text = "The code looks great! PASS."
        reviewer = ReviewerInfo(model="test", provider="test", role="test")
        v = _parse_verdict_json(text, "o-1", "t-1", reviewer)
        assert v.verdict == VerdictOutcome.PASS

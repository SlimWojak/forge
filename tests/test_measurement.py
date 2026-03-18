"""Tests for F013 (Boundary), F014 (Benchmark), F015 (Desloppify Mechanical)."""

from __future__ import annotations

from pathlib import Path

import pytest

from forge.boundary.measurement import (
    BoundaryRecord,
    BoundaryTracker,
    ClassificationInfo,
    CostInfo,
    OutcomeInfo,
    WorkerInfo,
)
from forge.enforcement.quality import (
    DesloppifyMechanical,
    MechanicalScanResult,
    QualityIssue,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(
    task_id: str,
    first_pass: bool = True,
    difficulty: str = "local-reasoning",
    tags: list[str] | None = None,
    cost: float = 0.01,
) -> BoundaryRecord:
    return BoundaryRecord(
        task_id=task_id,
        mission_id="m1",
        mission_mode="delivery",
        timestamp="2026-03-18T10:00:00Z",
        classification=ClassificationInfo(
            difficulty_class=difficulty,
            classified_by="planner",
            classification_confidence=0.8,
        ),
        worker=WorkerInfo(model="qwen3.5-35b"),
        outcome=OutcomeInfo(
            first_pass_success=first_pass,
            total_iterations=1 if first_pass else 2,
            final_verdict="PASS" if first_pass else "FAIL",
            error_taxonomy_tags=tags or [],
        ),
        cost=CostInfo(
            local_tokens=5000,
            frontier_tokens_in=3000,
            frontier_tokens_out=800,
            frontier_cost_usd=cost,
        ),
    )


# ---------------------------------------------------------------------------
# F013: Boundary Measurement
# ---------------------------------------------------------------------------


class TestBoundaryRecord:
    """test_boundary_record — serialization and storage."""

    def test_to_json(self) -> None:
        rec = _make_record("t-001")
        data = rec.to_json()
        assert data["task_id"] == "t-001"
        assert data["mission_mode"] == "delivery"
        assert data["outcome"]["first_pass_success"] is True

    def test_from_json_round_trip(self) -> None:
        rec = _make_record("t-002", first_pass=False, tags=["missing-tests"])
        data = rec.to_json()
        restored = BoundaryRecord.from_json(data)
        assert restored.task_id == "t-002"
        assert restored.outcome.first_pass_success is False


class TestBoundarySummary:
    """test_boundary_summary — report generation."""

    def test_generate_report(self, tmp_path: Path) -> None:
        tracker = BoundaryTracker(project_root=tmp_path)
        tracker.record(_make_record("t-001", first_pass=True))
        tracker.record(_make_record("t-002", first_pass=False))
        tracker.record(_make_record("t-003", first_pass=True))
        report = tracker.generate_report()
        assert "3" in report  # total tasks
        assert "2/3" in report  # first-pass
        assert "66%" in report or "67%" in report

    def test_report_by_type(self, tmp_path: Path) -> None:
        tracker = BoundaryTracker(project_root=tmp_path)
        tracker.record(_make_record("t-1", difficulty="mechanical", first_pass=True))
        tracker.record(_make_record("t-2", difficulty="architectural", first_pass=False))
        report = tracker.generate_report(by_type=True)
        assert "mechanical" in report
        assert "architectural" in report

    def test_empty_report(self, tmp_path: Path) -> None:
        tracker = BoundaryTracker(project_root=tmp_path)
        report = tracker.generate_report()
        assert "No boundary data" in report

    def test_first_pass_rate(self, tmp_path: Path) -> None:
        tracker = BoundaryTracker(project_root=tmp_path)
        tracker.record(_make_record("t-1", first_pass=True))
        tracker.record(_make_record("t-2", first_pass=True))
        tracker.record(_make_record("t-3", first_pass=False))
        assert tracker.get_first_pass_rate() == pytest.approx(2 / 3, abs=0.01)

    def test_generate_taxonomy(self, tmp_path: Path) -> None:
        tracker = BoundaryTracker(project_root=tmp_path)
        tracker.record(_make_record("t-1", first_pass=False, tags=["missing-tests"]))
        tracker.record(_make_record(
            "t-2", first_pass=False, tags=["missing-tests", "incorrect-logic"],
        ))
        report = tracker.generate_taxonomy()
        assert "missing-tests" in report
        assert "incorrect-logic" in report

    def test_data_persisted_to_jsonl(self, tmp_path: Path) -> None:
        tracker = BoundaryTracker(project_root=tmp_path)
        tracker.record(_make_record("t-001"))
        jsonl = (tmp_path / ".forge" / "boundary-data.jsonl").read_text()
        assert "t-001" in jsonl


# ---------------------------------------------------------------------------
# F015: Desloppify Mechanical Scan
# ---------------------------------------------------------------------------


@pytest.fixture()
def clean_py_file(tmp_path: Path) -> Path:
    f = tmp_path / "clean.py"
    f.write_text(
        "import os\n\n"
        "def hello():\n"
        "    return os.getcwd()\n"
    )
    return f


@pytest.fixture()
def messy_py_file(tmp_path: Path) -> Path:
    f = tmp_path / "messy.py"
    # Unused import, long function, high complexity
    lines = [
        "import os",
        "import sys",  # unused
        "import json",  # unused
        "",
        "def complex_func(x):",
    ]
    # Add many if branches for complexity
    for i in range(12):
        lines.append(f"    if x == {i}:")
        lines.append(f"        return {i}")
    lines.append("    return -1")
    lines.append("")
    # A very long function
    lines.append("def long_func():")
    for i in range(60):
        lines.append(f"    x_{i} = {i}")
    lines.append("    return x_0")
    lines.append("")
    # Deep nesting
    lines.append("def nested_func():")
    lines.append("    if True:")
    lines.append("        for i in range(10):")
    lines.append("            if i > 5:")
    lines.append("                while True:")
    lines.append("                    if i > 7:")
    lines.append("                        break")
    lines.append("    return 0")
    f.write_text("\n".join(lines) + "\n")
    return f


class TestMechanicalScan:
    """test_mechanical_scan — Desloppify mechanical quality detection."""

    def test_clean_file_high_score(self, clean_py_file: Path) -> None:
        scanner = DesloppifyMechanical()
        result = scanner.scan([str(clean_py_file)])
        assert isinstance(result, MechanicalScanResult)
        assert result.score >= 90

    def test_messy_file_low_score(self, messy_py_file: Path) -> None:
        scanner = DesloppifyMechanical()
        result = scanner.scan([str(messy_py_file)])
        assert result.score <= 90
        assert len(result.issues) >= 3

    def test_detects_unused_imports(self, messy_py_file: Path) -> None:
        scanner = DesloppifyMechanical()
        issues = scanner.detect_dead_code(str(messy_py_file))
        unused = [i for i in issues if "Unused import" in i.detail]
        assert len(unused) >= 2  # sys, json

    def test_detects_complexity(self, messy_py_file: Path) -> None:
        scanner = DesloppifyMechanical()
        issues = scanner.detect_complexity(str(messy_py_file))
        assert len(issues) >= 1
        assert issues[0].function == "complex_func"

    def test_detects_function_length(self, messy_py_file: Path) -> None:
        scanner = DesloppifyMechanical()
        issues = scanner.detect_function_length(str(messy_py_file))
        long_funcs = [i for i in issues if i.function == "long_func"]
        assert len(long_funcs) >= 1

    def test_detects_nesting_depth(self, messy_py_file: Path) -> None:
        scanner = DesloppifyMechanical()
        issues = scanner.detect_nesting_depth(str(messy_py_file))
        nested = [i for i in issues if i.function == "nested_func"]
        assert len(nested) >= 1

    def test_score_computation(self) -> None:
        scanner = DesloppifyMechanical()
        issues = [
            QualityIssue(file="a.py", issue_type="dead_code", detail="unused"),
            QualityIssue(file="a.py", issue_type="complexity", detail="high"),
            QualityIssue(file="a.py", issue_type="length", detail="long"),
        ]
        # dead_code*1 + complexity*3 + length*2 = 6
        assert scanner.compute_score(issues) == 94

    def test_nonexistent_file(self) -> None:
        scanner = DesloppifyMechanical()
        result = scanner.scan(["/nonexistent/file.py"])
        assert result.score == 100
        assert len(result.issues) == 0

    def test_forge_quality_command_output(self, clean_py_file: Path) -> None:
        scanner = DesloppifyMechanical()
        result = scanner.scan([str(clean_py_file)])
        assert isinstance(result.score, int)
        assert 0 <= result.score <= 100

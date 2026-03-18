"""Tests for FORGE ACI tools — Agent-Computer Interface.

Separate test file per Opus Advisor guidance. Tests follow naming
from feature_list.json success criteria.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from forge.aci.tools import (
    ViewResult,
    _reset_view_positions,
    view_file,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_positions():
    """Reset the view_file position tracker between tests."""
    _reset_view_positions()
    yield
    _reset_view_positions()


@pytest.fixture()
def sample_file(tmp_path: Path) -> Path:
    """Create a sample text file with 50 numbered lines."""
    f = tmp_path / "sample.py"
    content = "\n".join(f"# line {i}" for i in range(1, 51))
    f.write_text(content)
    return f


@pytest.fixture()
def binary_file(tmp_path: Path) -> Path:
    """Create a binary file with null bytes."""
    f = tmp_path / "data.bin"
    f.write_bytes(b"\x00\x01\x02\xff" * 100)
    return f


@pytest.fixture()
def empty_file(tmp_path: Path) -> Path:
    """Create an empty file."""
    f = tmp_path / "empty.txt"
    f.write_text("")
    return f


# ---------------------------------------------------------------------------
# F001: view_file
# ---------------------------------------------------------------------------


class TestViewFileBasic:
    """test_view_file_basic — basic reading and structured output."""

    def test_returns_view_result(self, sample_file: Path) -> None:
        result = view_file(str(sample_file))
        assert isinstance(result, ViewResult)

    def test_structured_fields(self, sample_file: Path) -> None:
        result = view_file(str(sample_file))
        assert result.path == str(sample_file.resolve())
        assert result.start_line == 1
        assert result.total_lines == 50
        assert result.end_line <= 50
        assert isinstance(result.content, str)
        assert isinstance(result.truncated, bool)

    def test_content_has_line_numbers(self, sample_file: Path) -> None:
        result = view_file(str(sample_file), start_line=1, num_lines=3)
        lines = result.content.strip().split("\n")
        assert len(lines) == 3
        assert "1 |" in lines[0]
        assert "# line 1" in lines[0]
        assert "2 |" in lines[1]
        assert "3 |" in lines[2]

    def test_start_line_parameter(self, sample_file: Path) -> None:
        result = view_file(str(sample_file), start_line=10, num_lines=5)
        assert result.start_line == 10
        assert result.end_line == 14
        assert "# line 10" in result.content

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            view_file("/nonexistent/path/file.txt")

    def test_empty_file(self, empty_file: Path) -> None:
        result = view_file(str(empty_file))
        assert result.total_lines == 0
        assert result.truncated is False


class TestViewFileBounds:
    """test_view_file_bounds — bounds checking and capping."""

    def test_num_lines_capped_at_200(self, sample_file: Path) -> None:
        result = view_file(str(sample_file), start_line=1, num_lines=500)
        # 50-line file, so all lines returned but num_lines was capped internally
        assert result.end_line == 50

    def test_start_line_beyond_eof(self, sample_file: Path) -> None:
        result = view_file(str(sample_file), start_line=999)
        # Should clamp, not crash
        assert result.start_line == 50
        assert result.total_lines == 50

    def test_start_line_below_one_raises(self, sample_file: Path) -> None:
        with pytest.raises(ValueError, match="start_line must be >= 1"):
            view_file(str(sample_file), start_line=0)

    def test_num_lines_below_one_raises(self, sample_file: Path) -> None:
        with pytest.raises(ValueError, match="num_lines must be >= 1"):
            view_file(str(sample_file), num_lines=0)

    def test_truncated_flag_true(self, sample_file: Path) -> None:
        result = view_file(str(sample_file), start_line=1, num_lines=10)
        assert result.truncated is True

    def test_truncated_flag_false_at_eof(self, sample_file: Path) -> None:
        result = view_file(str(sample_file), start_line=1, num_lines=200)
        assert result.truncated is False

    def test_window_at_end_of_file(self, sample_file: Path) -> None:
        result = view_file(str(sample_file), start_line=45, num_lines=100)
        assert result.start_line == 45
        assert result.end_line == 50
        assert result.truncated is False


class TestViewFilePositionMemory:
    """test_view_file_position_memory — stateful cursor across calls."""

    def test_continues_from_last_position(self, sample_file: Path) -> None:
        r1 = view_file(str(sample_file), num_lines=10)
        assert r1.start_line == 1
        assert r1.end_line == 10

        r2 = view_file(str(sample_file), num_lines=10)
        assert r2.start_line == 11
        assert r2.end_line == 20

    def test_explicit_start_overrides_memory(self, sample_file: Path) -> None:
        view_file(str(sample_file), num_lines=10)
        r2 = view_file(str(sample_file), start_line=5, num_lines=5)
        assert r2.start_line == 5
        assert r2.end_line == 9

    def test_separate_files_tracked_independently(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("\n".join(f"a{i}" for i in range(1, 21)))
        f2.write_text("\n".join(f"b{i}" for i in range(1, 21)))

        view_file(str(f1), num_lines=5)
        view_file(str(f2), num_lines=3)

        r1 = view_file(str(f1), num_lines=5)
        assert r1.start_line == 6  # continues from file a

        r2 = view_file(str(f2), num_lines=5)
        assert r2.start_line == 4  # continues from file b


class TestViewFileBinary:
    """test_view_file_binary — graceful handling of binary files."""

    def test_binary_file_raises_value_error(self, binary_file: Path) -> None:
        with pytest.raises(ValueError, match="Cannot view binary file"):
            view_file(str(binary_file))

    def test_binary_error_is_actionable(self, binary_file: Path) -> None:
        with pytest.raises(ValueError, match="FIX:"):
            view_file(str(binary_file))

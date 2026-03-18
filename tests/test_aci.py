"""Tests for FORGE ACI tools — Agent-Computer Interface.

Separate test file per Opus Advisor guidance. Tests follow naming
from feature_list.json success criteria.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from forge.aci.tools import (
    EditResult,
    SearchResult,
    ViewResult,
    _reset_view_positions,
    edit_file,
    rollback_edit,
    search_file,
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


# ---------------------------------------------------------------------------
# F002: edit_file
# ---------------------------------------------------------------------------


@pytest.fixture()
def python_file(tmp_path: Path) -> Path:
    """Create a valid Python file with 10 lines."""
    f = tmp_path / "module.py"
    content = "\n".join(
        [
            "import os",
            "",
            "def hello():",
            '    return "hello"',
            "",
            "def goodbye():",
            '    return "goodbye"',
            "",
            "x = 1",
            "y = 2",
        ]
    )
    f.write_text(content + "\n")
    return f


@pytest.fixture()
def ts_file(tmp_path: Path) -> Path:
    """Create a simple TypeScript/JS file."""
    f = tmp_path / "app.ts"
    content = "const x: number = 1;\nconsole.log(x);\n"
    f.write_text(content)
    return f


class TestEditFileBasic:
    """test_edit_file_basic — basic editing and structured output."""

    def test_returns_edit_result(self, python_file: Path) -> None:
        result = edit_file(str(python_file), 9, 9, "x = 42")
        assert isinstance(result, EditResult)

    def test_applied_fields(self, python_file: Path) -> None:
        result = edit_file(str(python_file), 9, 9, "x = 42")
        assert result.status == "applied"
        assert result.applied is True
        assert result.start_line == 9
        assert result.end_line == 9
        assert result.lines_removed == 1
        assert result.lines_added == 1
        assert result.lint_status == "pass"

    def test_content_actually_changed(self, python_file: Path) -> None:
        edit_file(str(python_file), 9, 9, "x = 42")
        content = python_file.read_text()
        assert "x = 42" in content
        assert "x = 1" not in content

    def test_multi_line_replacement(self, python_file: Path) -> None:
        result = edit_file(str(python_file), 3, 4, "def greet():\n    return 'hi'")
        assert result.lines_removed == 2
        assert result.lines_added == 2
        content = python_file.read_text()
        assert "def greet():" in content
        assert "def hello():" not in content

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            edit_file("/nonexistent/file.py", 1, 1, "x = 1")

    def test_start_line_below_one_raises(self, python_file: Path) -> None:
        with pytest.raises(ValueError, match="start_line must be >= 1"):
            edit_file(str(python_file), 0, 1, "x")

    def test_end_line_before_start_raises(self, python_file: Path) -> None:
        with pytest.raises(ValueError, match="end_line"):
            edit_file(str(python_file), 5, 3, "x")

    def test_start_beyond_eof_raises(self, python_file: Path) -> None:
        with pytest.raises(ValueError, match="exceeds file length"):
            edit_file(str(python_file), 999, 999, "x")

    def test_edit_non_python_file_skips_lint(self, tmp_path: Path) -> None:
        f = tmp_path / "data.txt"
        f.write_text("line1\nline2\nline3\n")
        result = edit_file(str(f), 2, 2, "changed")
        assert result.lint_status == "skipped"
        assert result.applied is True


class TestEditFileLintReject:
    """test_edit_file_lint_reject — lint check prevents bad edits."""

    def test_syntax_error_rejected(self, python_file: Path) -> None:
        result = edit_file(str(python_file), 3, 4, "def broken(:\n    pass")
        assert result.status == "rejected"
        assert result.applied is False
        assert result.lint_status == "fail"
        assert result.reason is not None
        assert "Syntax error" in result.reason

    def test_rejected_edit_not_written(self, python_file: Path) -> None:
        original = python_file.read_text()
        edit_file(str(python_file), 3, 4, "def broken(:\n    pass")
        assert python_file.read_text() == original

    def test_error_message_is_actionable(self, python_file: Path) -> None:
        result = edit_file(str(python_file), 3, 4, "def broken(:\n    pass")
        assert "WHY:" in result.reason
        assert "FIX:" in result.reason

    def test_valid_edit_passes_lint(self, python_file: Path) -> None:
        result = edit_file(str(python_file), 3, 4, "def new_func():\n    return 1")
        assert result.lint_status == "pass"
        assert result.applied is True


class TestEditFileRollback:
    """test_edit_file_rollback — backup creation and restore."""

    def test_backup_created_on_apply(self, python_file: Path) -> None:
        edit_file(str(python_file), 9, 9, "x = 99")
        backup = python_file.with_suffix(".py.forge-backup")
        assert backup.exists()
        assert "x = 1" in backup.read_text()

    def test_rollback_restores_original(self, python_file: Path) -> None:
        original = python_file.read_text()
        edit_file(str(python_file), 9, 9, "x = 99")
        assert "x = 99" in python_file.read_text()

        restored = rollback_edit(str(python_file))
        assert restored is True
        assert python_file.read_text() == original

    def test_rollback_returns_false_if_no_backup(self, python_file: Path) -> None:
        assert rollback_edit(str(python_file)) is False

    def test_no_backup_on_rejected_edit(self, python_file: Path) -> None:
        edit_file(str(python_file), 3, 4, "def broken(:\n    pass")
        backup = python_file.with_suffix(".py.forge-backup")
        assert not backup.exists()


# ---------------------------------------------------------------------------
# F003: search_file
# ---------------------------------------------------------------------------


@pytest.fixture()
def searchable_file(tmp_path: Path) -> Path:
    """Create a file with varied content for search testing."""
    f = tmp_path / "search_target.py"
    content = "\n".join(
        [
            "import os",
            "import sys",
            "",
            "def hello_world():",
            '    print("hello world")',
            "",
            "def goodbye_world():",
            '    print("goodbye world")',
            "",
            "class MyClass:",
            "    def method(self):",
            "        pass",
            "",
            "# TODO: fix this",
            "# TODO: refactor that",
            "x = 42",
        ]
    )
    f.write_text(content + "\n")
    return f


class TestSearchFileLiteral:
    """test_search_file_literal — literal string search."""

    def test_returns_search_result(self, searchable_file: Path) -> None:
        result = search_file(str(searchable_file), "hello", literal=True)
        assert isinstance(result, SearchResult)

    def test_finds_matches(self, searchable_file: Path) -> None:
        result = search_file(str(searchable_file), "TODO", literal=True)
        assert result.total_matches == 2
        assert all(m.line_number > 0 for m in result.matches)

    def test_match_content(self, searchable_file: Path) -> None:
        result = search_file(str(searchable_file), "hello_world", literal=True)
        assert result.total_matches == 1
        assert "def hello_world" in result.matches[0].content

    def test_context_lines(self, searchable_file: Path) -> None:
        result = search_file(
            str(searchable_file), "hello_world", literal=True, context_lines=2
        )
        m = result.matches[0]
        assert len(m.context_before) <= 2
        assert len(m.context_after) <= 2

    def test_no_matches(self, searchable_file: Path) -> None:
        result = search_file(str(searchable_file), "nonexistent", literal=True)
        assert result.total_matches == 0
        assert result.truncated is False

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            search_file("/nonexistent.py", "pattern")

    def test_path_in_result(self, searchable_file: Path) -> None:
        result = search_file(str(searchable_file), "x", literal=True)
        assert result.path == str(searchable_file.resolve())
        assert result.pattern == "x"


class TestSearchFileRegex:
    """test_search_file_regex — regex pattern search."""

    def test_regex_pattern(self, searchable_file: Path) -> None:
        result = search_file(str(searchable_file), r"def \w+_world")
        assert result.total_matches == 2

    def test_regex_line_start(self, searchable_file: Path) -> None:
        result = search_file(str(searchable_file), r"^import")
        assert result.total_matches == 2

    def test_invalid_regex_raises(self, searchable_file: Path) -> None:
        with pytest.raises(ValueError, match="Invalid regex"):
            search_file(str(searchable_file), "[invalid")

    def test_invalid_regex_has_fix_hint(self, searchable_file: Path) -> None:
        with pytest.raises(ValueError, match="FIX:"):
            search_file(str(searchable_file), "[invalid")


class TestSearchFileBounds:
    """test_search_file_bounds — result truncation."""

    def test_truncation(self, tmp_path: Path) -> None:
        f = tmp_path / "many_matches.txt"
        content = "\n".join(f"match line {i}" for i in range(100))
        f.write_text(content)
        result = search_file(str(f), "match", literal=True, max_results=10)
        assert len(result.matches) == 10
        assert result.total_matches == 100
        assert result.truncated is True

    def test_max_results_hard_cap_at_50(self, tmp_path: Path) -> None:
        f = tmp_path / "many.txt"
        content = "\n".join(f"line {i}" for i in range(100))
        f.write_text(content)
        result = search_file(str(f), "line", literal=True, max_results=999)
        assert len(result.matches) == 50

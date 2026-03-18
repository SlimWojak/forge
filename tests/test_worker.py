"""Tests for FORGE Worker Agent (F007).

Uses a mock model to test the worker agent loop without
requiring real API endpoints. Tests follow naming from
feature_list.json success criteria.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from forge.aci.worker import (
    TOOL_DEFINITIONS,
    ToolCallRecord,
    WorkerResult,
    _dispatch_tool_call,
    run_worker,
)

# ---------------------------------------------------------------------------
# Mock model for testing
# ---------------------------------------------------------------------------


class MockModel:
    """A mock model that returns pre-scripted responses.

    Accepts a list of responses that are returned in order.
    Each response is an OpenAI-compatible dict.
    """

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = list(responses)
        self._call_count = 0
        self.messages_log: list[list[dict[str, Any]]] = []

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self.messages_log.append(list(messages))
        if self._call_count >= len(self._responses):
            return _text_response("I have completed the task.")
        resp = self._responses[self._call_count]
        self._call_count += 1
        return resp


class ErrorModel:
    """A model that always raises an exception."""

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        raise ConnectionError("Model endpoint unavailable")


# ---------------------------------------------------------------------------
# Helper functions for building mock responses
# ---------------------------------------------------------------------------


def _text_response(content: str) -> dict[str, Any]:
    """Create a mock text completion response."""
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": content,
            }
        }]
    }


def _tool_call_response(calls: list[dict[str, Any]]) -> dict[str, Any]:
    """Create a mock tool_call completion response.

    calls: list of {"name": "tool_name", "arguments": {...}}
    """
    tool_calls = []
    for i, call in enumerate(calls):
        tool_calls.append({
            "id": f"call_{i}",
            "type": "function",
            "function": {
                "name": call["name"],
                "arguments": json.dumps(call["arguments"]),
            },
        })
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "tool_calls": tool_calls,
            }
        }]
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Create a simple workspace with a Python file."""
    src = tmp_path / "hello.py"
    src.write_text('def greet(name):\n    return f"Hello, {name}"\n')
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_hello.py").write_text(
        "from hello import greet\n\n"
        "def test_greet():\n"
        '    assert greet("World") == "Hello, World"\n'
    )
    return tmp_path


# ---------------------------------------------------------------------------
# F007: Worker agent loop
# ---------------------------------------------------------------------------


class TestWorkerSimpleTask:
    """test_worker_simple_task — basic worker execution with mock model."""

    def test_returns_worker_result(self, workspace: Path) -> None:
        model = MockModel([_text_response("Done. No changes needed.")])
        result = run_worker("Check the code", model, cwd=str(workspace))
        assert isinstance(result, WorkerResult)

    def test_completes_on_text_response(self, workspace: Path) -> None:
        model = MockModel([_text_response("Task complete.")])
        result = run_worker("Review the code", model, cwd=str(workspace))
        assert result.completed is True
        assert result.iterations == 1
        assert result.final_message == "Task complete."

    def test_dispatches_tool_calls(self, workspace: Path) -> None:
        model = MockModel([
            _tool_call_response([{
                "name": "view_file",
                "arguments": {"path": str(workspace / "hello.py")},
            }]),
            _text_response("I've reviewed the file. Looks good."),
        ])
        result = run_worker("Review hello.py", model, cwd=str(workspace))
        assert result.completed is True
        assert result.iterations == 2
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "view_file"

    def test_multiple_tool_calls_in_sequence(self, workspace: Path) -> None:
        model = MockModel([
            _tool_call_response([{
                "name": "view_file",
                "arguments": {"path": str(workspace / "hello.py")},
            }]),
            _tool_call_response([{
                "name": "search_file",
                "arguments": {
                    "path": str(workspace / "hello.py"),
                    "pattern": "def greet",
                },
            }]),
            _text_response("Found the function. Task complete."),
        ])
        result = run_worker("Find greet function", model, cwd=str(workspace))
        assert result.completed is True
        assert result.iterations == 3
        assert len(result.tool_calls) == 2

    def test_edit_file_tool_call(self, workspace: Path) -> None:
        src = workspace / "hello.py"
        model = MockModel([
            _tool_call_response([{
                "name": "edit_file",
                "arguments": {
                    "path": str(src),
                    "start_line": 1,
                    "end_line": 1,
                    "new_content": 'def greet(name: str) -> str:',
                },
            }]),
            _text_response("Added type hints to greet function."),
        ])
        result = run_worker("Add type hints", model, cwd=str(workspace))
        assert result.completed is True
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "edit_file"
        content = src.read_text()
        assert "name: str" in content

    def test_records_tool_call_details(self, workspace: Path) -> None:
        model = MockModel([
            _tool_call_response([{
                "name": "run_command",
                "arguments": {"command": "echo hello"},
            }]),
            _text_response("Done."),
        ])
        result = run_worker("Run echo", model, cwd=str(workspace))
        assert len(result.tool_calls) == 1
        tc = result.tool_calls[0]
        assert isinstance(tc, ToolCallRecord)
        assert tc.tool_name == "run_command"
        assert tc.duration_ms >= 0
        assert "hello" in tc.result_summary


class TestWorkerErrorHandling:
    """Worker handles tool errors and model errors gracefully."""

    def test_tool_error_returns_in_message(self, workspace: Path) -> None:
        model = MockModel([
            _tool_call_response([{
                "name": "view_file",
                "arguments": {"path": "/nonexistent/file.py"},
            }]),
            _text_response("File not found, completing anyway."),
        ])
        result = run_worker("View missing file", model, cwd=str(workspace))
        assert result.completed is True
        assert "error" in result.tool_calls[0].result_summary.lower()

    def test_model_error_captured(self, workspace: Path) -> None:
        model = ErrorModel()
        result = run_worker("Do something", model, cwd=str(workspace))
        assert result.completed is False
        assert result.error is not None
        assert "Model error" in result.error

    def test_unknown_tool_returns_error(self, workspace: Path) -> None:
        model = MockModel([
            _tool_call_response([{
                "name": "nonexistent_tool",
                "arguments": {},
            }]),
            _text_response("Tool not found, stopping."),
        ])
        result = run_worker("Use bad tool", model, cwd=str(workspace))
        assert result.completed is True
        assert "unknown tool" in result.tool_calls[0].result_summary.lower()


class TestWorkerBounds:
    """Worker respects iteration and tool call limits."""

    def test_max_iterations_enforced(self, workspace: Path) -> None:
        # Model always returns tool calls, never text
        responses = [
            _tool_call_response([{
                "name": "run_command",
                "arguments": {"command": "echo loop"},
            }])
            for _ in range(25)
        ]
        model = MockModel(responses)
        result = run_worker(
            "Infinite loop", model, cwd=str(workspace), max_iterations=5
        )
        assert result.completed is False
        assert result.iterations == 5
        assert "Max iterations" in result.error

    def test_max_tool_calls_enforced(self, workspace: Path) -> None:
        # Each model response has 3 tool calls
        responses = [
            _tool_call_response([
                {"name": "run_command", "arguments": {"command": f"echo {i}"}}
                for i in range(3)
            ])
            for _ in range(10)
        ]
        model = MockModel(responses)
        result = run_worker(
            "Many calls", model, cwd=str(workspace), max_tool_calls=5
        )
        assert result.completed is False
        assert "Max tool calls" in result.error

    def test_task_description_preserved(self, workspace: Path) -> None:
        model = MockModel([_text_response("Done")])
        result = run_worker("My specific task", model)
        assert result.task_description == "My specific task"


class TestToolDefinitions:
    """Tool definitions are properly structured."""

    def test_all_tools_have_names(self) -> None:
        for tool in TOOL_DEFINITIONS:
            assert "function" in tool
            assert "name" in tool["function"]

    def test_expected_tools_present(self) -> None:
        names = {t["function"]["name"] for t in TOOL_DEFINITIONS}
        expected = {
            "view_file", "edit_file", "search_file",
            "run_command", "run_tests", "codemap",
        }
        assert expected.issubset(names)


class TestToolDispatch:
    """_dispatch_tool_call works correctly for each tool."""

    def test_dispatch_view_file(self, workspace: Path) -> None:
        result = _dispatch_tool_call(
            "view_file", {"path": str(workspace / "hello.py")}
        )
        data = json.loads(result)
        assert "content" in data
        assert "greet" in data["content"]

    def test_dispatch_search_file(self, workspace: Path) -> None:
        result = _dispatch_tool_call(
            "search_file",
            {"path": str(workspace / "hello.py"), "pattern": "def"},
        )
        data = json.loads(result)
        assert data["total_matches"] >= 1

    def test_dispatch_run_command(self) -> None:
        result = _dispatch_tool_call(
            "run_command", {"command": "echo test_dispatch"}
        )
        data = json.loads(result)
        assert data["exit_code"] == 0
        assert "test_dispatch" in data["stdout"]

    def test_dispatch_error_returns_json(self) -> None:
        result = _dispatch_tool_call(
            "view_file", {"path": "/nonexistent"}
        )
        data = json.loads(result)
        assert "error" in data

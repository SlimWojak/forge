"""FORGE Worker Agent — executes tasks using ACI tools.

The worker receives a task description, uses ACI tools to implement
it via structured function calling, and produces git commits. It
operates within bounded limits (max iterations, max tokens) and
records all actions for observability.

See: FORGE_ARCHITECTURE_v0.2.md §3, §11
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from forge.aci.tools import (
    CommandResult,
    EditResult,
    SearchResult,
    ViewResult,
    codemap,
    edit_file,
    run_command,
    run_tests,
    search_file,
    view_file,
)

# ---------------------------------------------------------------------------
# Tool definitions for OpenAI function calling format
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "view_file",
            "description": "View a file with line numbers. Stateful — remembers position.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "start_line": {
                        "type": "integer",
                        "description": "First line to display (1-indexed). Omit to continue.",
                    },
                    "num_lines": {
                        "type": "integer",
                        "description": "Number of lines to show (max 200, default 100)",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace lines start_line..end_line with new content. Lint-checked.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "new_content": {"type": "string"},
                },
                "required": ["path", "start_line", "end_line", "new_content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_file",
            "description": "Search for a pattern in a file (regex or literal).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "pattern": {"type": "string"},
                    "literal": {"type": "boolean", "description": "Literal match (default: regex)"},
                    "max_results": {"type": "integer"},
                },
                "required": ["path", "pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute an approved shell command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run project tests via pytest.",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_path": {"type": "string", "description": "Specific test path or empty"},
                    "timeout": {"type": "integer"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "codemap",
            "description": "Tree-sitter structural summary of files (signatures only).",
            "parameters": {
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File paths to map",
                    },
                },
                "required": ["paths"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Model interface protocol (for mockability)
# ---------------------------------------------------------------------------


class ModelInterface(Protocol):
    """Protocol for the model backend used by the worker.

    Allows mocking in tests without requiring real API endpoints.
    """

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Send messages and return a completion response.

        Returns an OpenAI-compatible response dict with:
        - choices[0].message.content (text) or
        - choices[0].message.tool_calls (list of tool calls)
        """
        ...


# ---------------------------------------------------------------------------
# Tool call result serialization
# ---------------------------------------------------------------------------


def _serialize_tool_result(result: Any) -> str:
    """Convert an ACI tool result to a JSON string for the model."""
    if isinstance(result, ViewResult):
        return json.dumps({
            "path": result.path,
            "start_line": result.start_line,
            "end_line": result.end_line,
            "total_lines": result.total_lines,
            "truncated": result.truncated,
            "content": result.content,
        })
    elif isinstance(result, EditResult):
        return json.dumps({
            "status": result.status,
            "path": result.path,
            "lines_added": result.lines_added,
            "lines_removed": result.lines_removed,
            "lint_status": result.lint_status,
            "applied": result.applied,
            "reason": result.reason,
        })
    elif isinstance(result, SearchResult):
        return json.dumps({
            "path": result.path,
            "pattern": result.pattern,
            "total_matches": result.total_matches,
            "truncated": result.truncated,
            "matches": [
                {"line_number": m.line_number, "content": m.content}
                for m in result.matches[:10]
            ],
        })
    elif isinstance(result, CommandResult):
        return json.dumps({
            "command": result.command,
            "exit_code": result.exit_code,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:1000],
            "timed_out": result.timed_out,
            "blocked": result.blocked,
        })
    elif isinstance(result, dict):
        return json.dumps(result)
    else:
        return json.dumps({"result": str(result)})


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------


def _dispatch_tool_call(
    name: str, arguments: dict[str, Any], cwd: str | None = None
) -> str:
    """Execute an ACI tool and return the serialized result."""
    try:
        if name == "view_file":
            r = view_file(
                path=arguments["path"],
                start_line=arguments.get("start_line"),
                num_lines=arguments.get("num_lines", 100),
            )
            return _serialize_tool_result(r)

        elif name == "edit_file":
            r = edit_file(
                path=arguments["path"],
                start_line=arguments["start_line"],
                end_line=arguments["end_line"],
                new_content=arguments["new_content"],
            )
            return _serialize_tool_result(r)

        elif name == "search_file":
            r = search_file(
                path=arguments["path"],
                pattern=arguments["pattern"],
                literal=arguments.get("literal", False),
                max_results=arguments.get("max_results", 50),
            )
            return _serialize_tool_result(r)

        elif name == "run_command":
            r = run_command(
                command=arguments["command"],
                timeout=arguments.get("timeout", 30),
                cwd=cwd,
            )
            return _serialize_tool_result(r)

        elif name == "run_tests":
            r = run_tests(
                test_path=arguments.get("test_path", ""),
                timeout=arguments.get("timeout", 120),
                cwd=cwd,
            )
            return json.dumps({
                "status": r.status,
                "passed": r.passed,
                "failed": r.failed,
                "errors": r.errors,
                "skipped": r.skipped,
                "timed_out": r.timed_out,
            })

        elif name == "codemap":
            r = codemap(paths=arguments.get("paths", []))
            return json.dumps({"files": r.files})

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# Worker agent
# ---------------------------------------------------------------------------


@dataclass
class ToolCallRecord:
    """Record of a single tool call for tracing."""

    tool_name: str
    arguments: dict[str, Any]
    result_summary: str
    duration_ms: int


@dataclass
class WorkerResult:
    """Result of a worker execution."""

    task_description: str
    completed: bool
    iterations: int
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    final_message: str = ""
    error: str | None = None
    total_tokens_estimate: int = 0


WORKER_SYSTEM_PROMPT = """\
You are a FORGE worker agent. Your job is to implement the \
given task using the available tools.

Rules:
- Use view_file to understand existing code before editing
- Use edit_file to make changes (edits are lint-checked before applying)
- Use search_file to find relevant code
- Use run_tests after making changes to verify correctness
- Use codemap to understand file structure
- Use run_command for git operations and other approved commands
- Work methodically: understand → plan → implement → test → verify
- If a tool call fails, read the error message and adjust your approach
- When the task is complete and tests pass, respond with a summary of changes made

Do NOT:
- Make changes without understanding the existing code first
- Skip running tests after changes
- Make multiple unrelated changes at once
"""


def run_worker(
    task_description: str,
    model: ModelInterface,
    cwd: str | None = None,
    max_iterations: int = 20,
    max_tool_calls: int = 50,
) -> WorkerResult:
    """Execute a task using the worker agent loop.

    The worker iterates: call model -> dispatch tool calls -> feed results
    back -> repeat until the model indicates completion or limits are hit.

    Args:
        task_description: What the worker should implement.
        model: Model backend (real or mock) implementing ModelInterface.
        cwd: Working directory for commands/tests.
        max_iterations: Max model calls before stopping. Default 20.
        max_tool_calls: Max total tool calls before stopping. Default 50.

    Returns:
        WorkerResult with completion status, tool call records, and summary.

    See: FORGE_ARCHITECTURE_v0.2.md §3, §11
    """
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": WORKER_SYSTEM_PROMPT},
        {"role": "user", "content": f"Task: {task_description}"},
    ]

    all_tool_calls: list[ToolCallRecord] = []
    total_tool_call_count = 0

    for iteration in range(max_iterations):
        try:
            response = model.chat_completion(
                messages=messages,
                tools=TOOL_DEFINITIONS,
            )
        except Exception as e:
            return WorkerResult(
                task_description=task_description,
                completed=False,
                iterations=iteration + 1,
                tool_calls=all_tool_calls,
                error=f"Model error: {e}",
            )

        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})

        # If the model returns tool calls, dispatch them
        tool_calls = message.get("tool_calls")
        if tool_calls:
            messages.append(message)

            for tc in tool_calls:
                if total_tool_call_count >= max_tool_calls:
                    return WorkerResult(
                        task_description=task_description,
                        completed=False,
                        iterations=iteration + 1,
                        tool_calls=all_tool_calls,
                        error=f"Max tool calls ({max_tool_calls}) exceeded",
                    )

                fn = tc.get("function", {})
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}

                start_t = time.monotonic()
                result_str = _dispatch_tool_call(name, args, cwd=cwd)
                elapsed = int((time.monotonic() - start_t) * 1000)

                record = ToolCallRecord(
                    tool_name=name,
                    arguments=args,
                    result_summary=result_str[:500],
                    duration_ms=elapsed,
                )
                all_tool_calls.append(record)
                total_tool_call_count += 1

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", f"call_{total_tool_call_count}"),
                    "content": result_str,
                })
        else:
            # No tool calls — model is responding with text (done or stuck)
            content = message.get("content", "")
            return WorkerResult(
                task_description=task_description,
                completed=True,
                iterations=iteration + 1,
                tool_calls=all_tool_calls,
                final_message=content,
            )

    return WorkerResult(
        task_description=task_description,
        completed=False,
        iterations=max_iterations,
        tool_calls=all_tool_calls,
        error=f"Max iterations ({max_iterations}) exceeded",
    )

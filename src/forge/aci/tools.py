"""FORGE ACI Tool Definitions — Agent-Computer Interface.

Every tool returns structured JSON, is bounded, and provides
immediate, actionable error messages. The harness normalizes
the interface so tools behave identically regardless of which
model invokes them.

Core Phase 1 tools: view_file, edit_file, search_file, run_command, run_tests
Extended tools: create_file, find_file, search_dir, tree, codemap,
                git_status, git_commit, git_diff, query_traces

See: FORGE_ARCHITECTURE_v0.2.md §11
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Base classes
# ---------------------------------------------------------------------------


class ToolStatus(Enum):
    """Status of a tool execution result."""

    SUCCESS = "success"
    ERROR = "error"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ToolResult:
    """Base result type for all ACI tools.

    Every tool returns a ToolResult subclass with structured data.
    Use the factory methods for consistent construction.
    """

    status: ToolStatus
    data: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None

    @classmethod
    def success(cls, data: dict[str, Any]) -> ToolResult:
        """Create a successful tool result."""
        return cls(status=ToolStatus.SUCCESS, data=data)

    @classmethod
    def error(cls, message: str) -> ToolResult:
        """Create an error tool result with an actionable message."""
        return cls(status=ToolStatus.ERROR, error_message=message)

    @classmethod
    def rejected(cls, reason: str) -> ToolResult:
        """Create a rejected result (blocked by hook or policy)."""
        return cls(status=ToolStatus.REJECTED, error_message=reason)

    def to_json(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        result: dict[str, Any] = {"status": self.status.value}
        if self.data:
            result.update(self.data)
        if self.error_message:
            result["error"] = self.error_message
        return result


class Tool:
    """Base class for custom ACI tool plugins.

    Custom tools placed in .forge/tools/ inherit from this class.
    See: FORGE_ARCHITECTURE_v0.2.md §11.2

    Example::

        class CustomDbQuery(Tool):
            name = "db_query"
            description = "Execute a read-only SQL query"
            parameters = {"query": {"type": "string"}}

            def execute(self, **kwargs) -> ToolResult:
                ...
    """

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {}

    def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given arguments. Override in subclasses."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Structured result types for Phase 1 core tools
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ViewResult:
    """Result of viewing a file with line numbers.

    The viewer is stateful — it remembers the last position viewed
    so the agent can navigate large files incrementally.
    """

    path: str
    start_line: int
    end_line: int
    content: str
    total_lines: int


@dataclass(frozen=True)
class EditResult:
    """Result of an edit_file operation.

    Edits are validated by Layer 1 hooks (syntax check, secret scan)
    before being applied. A rejected edit is never written to disk.
    """

    status: str  # "applied" | "rejected"
    path: str
    reason: str | None = None


@dataclass(frozen=True)
class SearchMatch:
    """A single search match within a file."""

    line: int
    content: str


@dataclass(frozen=True)
class SearchResult:
    """Result of searching within a single file.

    Bounded to max_results to prevent context flooding.
    """

    matches: list[SearchMatch]
    total: int
    truncated: bool


@dataclass(frozen=True)
class CommandResult:
    """Result of running a shell command.

    Commands are allowlist-checked by Layer 1 hooks before execution.
    Dangerous commands are blocked mechanically.
    """

    stdout: str
    stderr: str
    exit_code: int


@dataclass(frozen=True)
class TestResult:
    """Result of running the test suite.

    Includes pass/fail counts and structured error information
    for failed tests so the worker can act on failures directly.
    """

    status: str  # "pass" | "fail" | "error"
    passed: int
    failed: int
    errors: list[dict[str, Any]]
    coverage_delta: str | None = None


@dataclass(frozen=True)
class CreateResult:
    """Result of creating a new file."""

    status: str  # "created" | "rejected"
    path: str
    reason: str | None = None


@dataclass(frozen=True)
class FindResult:
    """Result of finding files by name pattern."""

    files: list[str]
    total: int
    truncated: bool


@dataclass(frozen=True)
class DirSearchResult:
    """Result of searching across a directory."""

    files: list[dict[str, Any]]  # [{"path": ..., "matches": [...]}]
    total: int
    truncated: bool


@dataclass(frozen=True)
class TreeResult:
    """Result of displaying directory structure."""

    tree: str
    depth: int


@dataclass(frozen=True)
class CodemapResult:
    """Result of tree-sitter structural summary."""

    files: list[dict[str, Any]]  # [{"path": ..., "signatures": [...]}]


@dataclass(frozen=True)
class GitStatusResult:
    """Result of querying git state."""

    branch: str
    modified: list[str]
    staged: list[str]
    untracked: list[str]


@dataclass(frozen=True)
class GitCommitResult:
    """Result of creating a git commit."""

    status: str  # "committed" | "rejected"
    sha: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class GitDiffResult:
    """Result of showing diff against main."""

    diff: str
    truncated: bool


@dataclass(frozen=True)
class QueryTracesResult:
    """Result of SQL query against DuckDB traces."""

    columns: list[str]
    rows: list[list[Any]]
    truncated: bool


# ---------------------------------------------------------------------------
# Phase 1 Core Tools (5 primary + extended)
# ---------------------------------------------------------------------------


def view_file(
    path: str,
    start_line: int = 1,
    num_lines: int = 100,
) -> ViewResult:
    """View a file with line numbers, starting at the given line.

    The viewer is stateful and remembers position. Default window is
    100 lines to prevent context flooding. The agent navigates large
    files by adjusting start_line.

    Args:
        path: Absolute or project-relative path to the file.
        start_line: First line to display (1-indexed). Must be >= 1.
        num_lines: Number of lines to show. Max 200, default 100.

    Returns:
        ViewResult with path, line range, content, and total line count.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If start_line < 1 or num_lines < 1.

    TODO: Implement file reading with bounds checking (§11.1).
    TODO: Add stateful position tracking per session.
    TODO: Wire Layer 1 hooks for pre-read checks.
    """
    # Bounds validation
    if start_line < 1:
        raise ValueError(f"start_line must be >= 1, got {start_line}")
    if num_lines < 1:
        raise ValueError(f"num_lines must be >= 1, got {num_lines}")
    num_lines = min(num_lines, 200)  # Hard cap

    # TODO: Implement actual file reading
    raise NotImplementedError("view_file not yet implemented — see §11.1")


def edit_file(
    path: str,
    start_line: int,
    end_line: int,
    new_content: str,
) -> EditResult:
    """Replace lines start_line..end_line with new_content.

    Before applying, the edit is validated by Layer 1 hooks:
    - pre_edit: syntax_check (tree-sitter parse)
    - post_edit: auto_format + secret_scan

    A rejected edit is never written to disk. The error message
    explains WHAT went wrong, WHY it matters, and HOW to fix it.

    Args:
        path: Path to the file to edit.
        start_line: First line to replace (1-indexed, inclusive).
        end_line: Last line to replace (1-indexed, inclusive).
        new_content: Replacement content (may be multi-line string).

    Returns:
        EditResult with status "applied" or "rejected" and reason.

    TODO: Implement line replacement with bounds checking (§11.1).
    TODO: Wire Layer 1 pre_edit and post_edit hooks (§6.1).
    TODO: Track edits in observability pipeline.
    """
    if start_line < 1:
        raise ValueError(f"start_line must be >= 1, got {start_line}")
    if end_line < start_line:
        raise ValueError(f"end_line ({end_line}) must be >= start_line ({start_line})")

    raise NotImplementedError("edit_file not yet implemented — see §11.1")


def search_file(
    path: str,
    pattern: str,
    max_results: int = 50,
) -> SearchResult:
    """Search for a regex/literal pattern within a single file.

    Results are bounded to max_results to prevent context flooding.
    Returns line numbers and matched content for each hit.

    Args:
        path: Path to the file to search.
        pattern: Regex or literal pattern to match.
        max_results: Maximum number of results to return. Default 50.

    Returns:
        SearchResult with matches, total count, and truncation flag.

    TODO: Implement regex search with bounded output (§11.1).
    TODO: Support both regex and literal mode.
    """
    max_results = min(max_results, 50)  # Hard cap per spec

    raise NotImplementedError("search_file not yet implemented — see §11.1")


def run_command(
    command: str,
    timeout: int = 30,
) -> CommandResult:
    """Execute a shell command after allowlist validation.

    Commands are checked against the allowlist in .forge/hooks.yaml
    before execution. Blocked commands return a rejected result with
    the allowed command list.

    Args:
        command: Shell command string to execute.
        timeout: Maximum execution time in seconds. Default 30.

    Returns:
        CommandResult with stdout, stderr, and exit code.

    TODO: Implement subprocess execution with timeout (§11.1).
    TODO: Wire Layer 1 pre_command allowlist hook (§6.1).
    TODO: Capture in observability pipeline.
    """
    if timeout < 1:
        raise ValueError(f"timeout must be >= 1, got {timeout}")
    timeout = min(timeout, 300)  # Hard cap at 5 minutes

    raise NotImplementedError("run_command not yet implemented — see §11.1")


def run_tests(
    test_path: str = "",
    timeout: int = 120,
) -> TestResult:
    """Execute the project test suite (or specific test file/function).

    Runs pytest by default. Captures structured pass/fail counts and
    error details so the worker can directly act on failures.

    Args:
        test_path: Specific test file or function. Empty string = full suite.
        timeout: Maximum execution time in seconds. Default 120.

    Returns:
        TestResult with status, counts, and error details.

    TODO: Implement pytest runner with structured output capture (§11.1).
    TODO: Parse test output into structured error list.
    TODO: Compute coverage delta if coverage is configured.
    """
    timeout = min(timeout, 600)  # Hard cap at 10 minutes

    raise NotImplementedError("run_tests not yet implemented — see §11.1")


# ---------------------------------------------------------------------------
# Extended Tools (stubs)
# ---------------------------------------------------------------------------


def create_file(path: str, content: str) -> CreateResult:
    """Create a new file with the given content.

    Validates through Layer 1 hooks (syntax check, secret scan)
    before writing. Returns rejected if the file already exists
    or fails validation.

    Args:
        path: Path for the new file.
        content: File content to write.

    Returns:
        CreateResult with status and path.

    TODO: Implement file creation with hook validation (§11.1).
    """
    raise NotImplementedError("create_file not yet implemented — see §11.1")


def find_file(pattern: str, max_results: int = 30) -> FindResult:
    """Find files matching a name/glob pattern.

    Searches the project directory. Results bounded to max_results.

    Args:
        pattern: Glob pattern (e.g., "*.py", "test_*.ts").
        max_results: Maximum files to return. Default 30.

    Returns:
        FindResult with file paths, total, and truncation flag.

    TODO: Implement glob-based file finder (§11.1).
    """
    raise NotImplementedError("find_file not yet implemented — see §11.1")


def search_dir(
    directory: str,
    pattern: str,
    max_results: int = 50,
) -> DirSearchResult:
    """Search for a pattern across all files in a directory.

    Searches recursively. Results bounded to max_results total matches.

    Args:
        directory: Directory to search in.
        pattern: Regex or literal pattern.
        max_results: Maximum total matches. Default 50.

    Returns:
        DirSearchResult with per-file matches.

    TODO: Implement recursive directory search (§11.1).
    """
    raise NotImplementedError("search_dir not yet implemented — see §11.1")


def tree(directory: str = ".", max_depth: int = 3) -> TreeResult:
    """Show directory structure up to a given depth.

    Depth-limited to prevent flooding context with large trees.

    Args:
        directory: Root directory. Default is project root.
        max_depth: Maximum depth to traverse. Default 3.

    Returns:
        TreeResult with formatted tree string.

    TODO: Implement depth-limited tree display (§11.1).
    """
    raise NotImplementedError("tree not yet implemented — see §11.1")


def codemap(paths: list[str] | None = None) -> CodemapResult:
    """Generate tree-sitter structural summary of files.

    Extracts function signatures, class definitions, imports, and
    exports using tree-sitter parsing. Returns signatures only —
    no implementation bodies.

    Args:
        paths: Specific files to map. None = all changed files.

    Returns:
        CodemapResult with per-file signature lists.

    TODO: Implement tree-sitter codemap pipeline (§4, §11.1).
    TODO: Support multiple languages via tree-sitter-languages.
    """
    raise NotImplementedError("codemap not yet implemented — see §11.1")


def git_status() -> GitStatusResult:
    """Get current git working tree state.

    Returns:
        GitStatusResult with branch, modified, staged, and untracked files.

    TODO: Implement git status parsing (§11.1, §12).
    """
    raise NotImplementedError("git_status not yet implemented — see §11.1")


def git_commit(message: str) -> GitCommitResult:
    """Create a git commit with an enforced message format.

    Commit messages must follow: [FORGE] <task-id>: <description>
    The harness validates the format before committing.

    Args:
        message: Commit message (format validated by harness).

    Returns:
        GitCommitResult with status and SHA.

    TODO: Implement commit with format validation (§11.1, §12.3).
    TODO: Wire post_commit hooks (desloppify_mechanical, architectural_lint).
    """
    raise NotImplementedError("git_commit not yet implemented — see §11.1")


def git_diff(max_lines: int = 500) -> GitDiffResult:
    """Show diff against the main branch.

    Output bounded to max_lines to prevent context flooding.

    Args:
        max_lines: Maximum lines of diff output. Default 500.

    Returns:
        GitDiffResult with diff text and truncation flag.

    TODO: Implement bounded git diff (§11.1).
    """
    raise NotImplementedError("git_diff not yet implemented — see §11.1")


def query_traces(sql: str, max_rows: int = 100) -> QueryTracesResult:
    """Execute a SQL query against the DuckDB observability database.

    Allows workers to inspect their own performance and trace history.
    Only SELECT queries are permitted.

    Args:
        sql: SQL SELECT query string.
        max_rows: Maximum rows to return. Default 100.

    Returns:
        QueryTracesResult with columns, rows, and truncation flag.

    See: FORGE_ARCHITECTURE_v0.2.md §10.3

    TODO: Implement DuckDB query with read-only enforcement (§10.3, §11.1).
    """
    if not sql.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed against the trace database")

    raise NotImplementedError("query_traces not yet implemented — see §10.3")


def browser_test(url: str, screenshot: bool = False) -> ToolResult:
    """Run a browser-based test against a URL.

    Phase 2+ will support Playwright screenshots as Oracle annexes.

    Args:
        url: URL to test.
        screenshot: Whether to capture a screenshot (Phase 2+).

    Returns:
        ToolResult with test outcome.

    TODO: Stub for Phase 2+ browser testing support.
    """
    raise NotImplementedError("browser_test is a Phase 2+ feature")

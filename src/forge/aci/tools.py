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
    truncated: bool = False


@dataclass(frozen=True)
class EditResult:
    """Result of an edit_file operation.

    Edits are validated by Layer 1 hooks (syntax check, secret scan)
    before being applied. A rejected edit is never written to disk.
    """

    status: str  # "applied" | "rejected"
    path: str
    start_line: int = 0
    end_line: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    lint_status: str = "skipped"  # "pass" | "fail" | "skipped"
    applied: bool = False
    reason: str | None = None


@dataclass(frozen=True)
class SearchMatch:
    """A single search match within a file."""

    line_number: int
    content: str
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SearchResult:
    """Result of searching within a single file.

    Bounded to max_results to prevent context flooding.
    """

    path: str
    pattern: str
    matches: list[SearchMatch]
    total_matches: int
    truncated: bool


@dataclass(frozen=True)
class CommandResult:
    """Result of running a shell command.

    Commands are allowlist-checked by Layer 1 hooks before execution.
    Dangerous commands are blocked mechanically.
    """

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int = 0
    timed_out: bool = False
    blocked: bool = False


@dataclass(frozen=True)
class TestResult:
    """Result of running the test suite.

    Includes pass/fail counts and structured error information
    for failed tests so the worker can act on failures directly.
    """

    test_path: str
    status: str  # "pass" | "fail" | "error"
    passed: int
    failed: int
    errors: int
    skipped: int
    duration_ms: int
    failures: list[dict[str, Any]] = field(default_factory=list)
    timed_out: bool = False


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
# Session-scoped position tracker for view_file
# ---------------------------------------------------------------------------

_view_positions: dict[str, int] = {}


def _reset_view_positions() -> None:
    """Reset the position tracker (used in tests)."""
    _view_positions.clear()


def _is_binary(path: Path, sample_size: int = 8192) -> bool:
    """Heuristic: file is binary if the first sample_size bytes contain null."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(sample_size)
        return b"\x00" in chunk
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Phase 1 Core Tools (5 primary + extended)
# ---------------------------------------------------------------------------


def view_file(
    path: str,
    start_line: int | None = None,
    num_lines: int = 100,
) -> ViewResult:
    """View a file with line numbers, starting at the given line.

    The viewer is stateful and remembers position. Default window is
    100 lines to prevent context flooding. The agent navigates large
    files by adjusting start_line.

    Args:
        path: Absolute or project-relative path to the file.
        start_line: First line to display (1-indexed). None = continue
                    from last position (or 1 if not viewed before).
        num_lines: Number of lines to show. Max 200, default 100.

    Returns:
        ViewResult with path, line range, content, total line count,
        and truncated flag.

    See: FORGE_ARCHITECTURE_v0.2.md §11.1
    """
    if num_lines < 1:
        raise ValueError(f"num_lines must be >= 1, got {num_lines}")
    num_lines = min(num_lines, 200)

    file_path = Path(path).resolve()
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    if _is_binary(file_path):
        raise ValueError(
            f"Cannot view binary file: {path}\n"
            "WHY: Binary files are not human-readable and would waste context tokens.\n"
            "FIX: Use a hex viewer or check if you meant a different file."
        )

    resolved_key = str(file_path)

    if start_line is None:
        start_line = _view_positions.get(resolved_key, 1)
    if start_line < 1:
        raise ValueError(f"start_line must be >= 1, got {start_line}")

    lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    total_lines = len(lines)

    # Clamp start_line to file length (return empty content at EOF rather than error)
    if start_line > total_lines:
        start_line = max(total_lines, 1)

    end_line = min(start_line + num_lines - 1, total_lines)
    selected = lines[start_line - 1 : end_line]

    numbered = "\n".join(
        f"{start_line + i:>6} | {line}" for i, line in enumerate(selected)
    )

    truncated = end_line < total_lines

    # Update position memory: next call continues after this window
    _view_positions[resolved_key] = end_line + 1

    return ViewResult(
        path=str(file_path),
        start_line=start_line,
        end_line=end_line,
        content=numbered,
        total_lines=total_lines,
        truncated=truncated,
    )


def _lint_check_python(source: str) -> tuple[bool, str | None]:
    """Check Python source for syntax errors using ast.parse."""
    import ast

    try:
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        msg = (
            f"Syntax error on line {e.lineno}, column {e.offset}: {e.msg}\n"
            "WHY: Applying this edit would create invalid Python that "
            "cannot be imported or executed.\n"
            "FIX: Correct the syntax error in the replacement content "
            "before retrying."
        )
        return False, msg


def _lint_check_typescript(source: str) -> tuple[bool, str | None]:
    """Basic TypeScript/JavaScript syntax check via Node.js."""
    import subprocess
    import tempfile

    try:
        with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False) as f:
            f.write(source)
            tmp_path = f.name
        result = subprocess.run(
            ["node", "--check", tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        Path(tmp_path).unlink(missing_ok=True)
        if result.returncode != 0:
            msg = (
                f"Syntax error: {result.stderr.strip()}\n"
                "WHY: Applying this edit would create invalid JavaScript/TypeScript.\n"
                "FIX: Correct the syntax error in the replacement content."
            )
            return False, msg
        return True, None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True, None  # Node not available; skip check gracefully


def rollback_edit(path: str) -> bool:
    """Restore a file from its .forge-backup. Returns True if restored."""
    file_path = Path(path).resolve()
    backup_path = file_path.with_suffix(file_path.suffix + ".forge-backup")
    if backup_path.is_file():
        backup_path.rename(file_path)
        return True
    return False


_LINT_CHECKERS: dict[str, Any] = {
    ".py": _lint_check_python,
    ".ts": _lint_check_typescript,
    ".tsx": _lint_check_typescript,
    ".js": _lint_check_typescript,
    ".jsx": _lint_check_typescript,
}


def edit_file(
    path: str,
    start_line: int,
    end_line: int,
    new_content: str,
) -> EditResult:
    """Replace lines start_line..end_line with new_content.

    Before applying, the edit is validated by lint check:
    - Python files: ast.parse syntax validation
    - TypeScript/JS files: node --check validation

    A rejected edit is never written to disk. Creates a backup
    before applying for rollback capability.

    Args:
        path: Path to the file to edit.
        start_line: First line to replace (1-indexed, inclusive).
        end_line: Last line to replace (1-indexed, inclusive).
        new_content: Replacement content (may be multi-line string).

    Returns:
        EditResult with status, line counts, lint_status, and applied flag.

    See: FORGE_ARCHITECTURE_v0.2.md §11.1
    """
    if start_line < 1:
        raise ValueError(f"start_line must be >= 1, got {start_line}")
    if end_line < start_line:
        raise ValueError(f"end_line ({end_line}) must be >= start_line ({start_line})")

    file_path = Path(path).resolve()
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    original = file_path.read_text(encoding="utf-8", errors="replace")
    lines = original.splitlines(keepends=True)
    total_lines = len(lines)

    if start_line > total_lines:
        raise ValueError(
            f"start_line ({start_line}) exceeds file length ({total_lines})"
        )
    if end_line > total_lines:
        end_line = total_lines

    # Build the new file content
    new_lines = new_content.splitlines(keepends=True)
    # Ensure last line has newline if original did
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"

    result_lines = lines[: start_line - 1] + new_lines + lines[end_line:]
    result_content = "".join(result_lines)

    lines_removed = end_line - start_line + 1
    lines_added = len(new_lines)

    # Lint check BEFORE applying
    suffix = file_path.suffix.lower()
    checker = _LINT_CHECKERS.get(suffix)
    lint_status = "skipped"

    if checker is not None:
        ok, error_msg = checker(result_content)
        if not ok:
            return EditResult(
                status="rejected",
                path=str(file_path),
                start_line=start_line,
                end_line=end_line,
                lines_added=lines_added,
                lines_removed=lines_removed,
                lint_status="fail",
                applied=False,
                reason=error_msg,
            )
        lint_status = "pass"

    # Create backup before applying
    backup_path = file_path.with_suffix(file_path.suffix + ".forge-backup")
    backup_path.write_text(original, encoding="utf-8")

    # Apply the edit
    file_path.write_text(result_content, encoding="utf-8")

    return EditResult(
        status="applied",
        path=str(file_path),
        start_line=start_line,
        end_line=end_line,
        lines_added=lines_added,
        lines_removed=lines_removed,
        lint_status=lint_status,
        applied=True,
    )


def search_file(
    path: str,
    pattern: str,
    max_results: int = 50,
    literal: bool = False,
    context_lines: int = 2,
) -> SearchResult:
    """Search for a regex/literal pattern within a single file.

    Results are bounded to max_results to prevent context flooding.
    Returns line numbers, matched content, and surrounding context.

    Args:
        path: Path to the file to search.
        pattern: Regex or literal pattern to match.
        max_results: Maximum number of results to return. Default 50, hard cap 50.
        literal: If True, treat pattern as a literal string (not regex).
        context_lines: Number of lines of context before and after each match.

    Returns:
        SearchResult with path, pattern, matches, total_matches, truncated flag.

    See: FORGE_ARCHITECTURE_v0.2.md §11.1
    """
    import re

    max_results = min(max_results, 50)

    file_path = Path(path).resolve()
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    text = file_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    if literal:
        compiled = re.compile(re.escape(pattern))
    else:
        try:
            compiled = re.compile(pattern)
        except re.error as e:
            raise ValueError(
                f"Invalid regex pattern: {e}\n"
                "FIX: Check the regex syntax or use literal=True for exact string matching."
            ) from e

    all_matches: list[SearchMatch] = []
    for i, line in enumerate(lines):
        if compiled.search(line):
            ctx_before = lines[max(0, i - context_lines) : i]
            ctx_after = lines[i + 1 : i + 1 + context_lines]
            all_matches.append(
                SearchMatch(
                    line_number=i + 1,
                    content=line,
                    context_before=ctx_before,
                    context_after=ctx_after,
                )
            )

    total = len(all_matches)
    truncated = total > max_results
    returned = all_matches[:max_results]

    return SearchResult(
        path=str(file_path),
        pattern=pattern,
        matches=returned,
        total_matches=total,
        truncated=truncated,
    )


_BLOCKED_PATTERNS: list[str] = [
    r"rm\s+-rf",
    r"curl\s.*\|\s*(bash|sh)",
    r"\bsudo\b",
    r"chmod\s+777",
    r"\beval\b",
]


def _is_command_blocked(command: str) -> str | None:
    """Check if a command matches any blocked pattern. Returns reason or None."""
    import re

    for pat in _BLOCKED_PATTERNS:
        if re.search(pat, command):
            return (
                f"Command blocked: matches dangerous pattern '{pat}'\n"
                "WHY: This command pattern is on the block list to prevent "
                "accidental destructive actions.\n"
                "FIX: Use a safer alternative or request an allowlist exception."
            )
    return None


def run_command(
    command: str,
    timeout: int = 30,
    cwd: str | None = None,
) -> CommandResult:
    """Execute a shell command after allowlist validation.

    Commands are checked against blocked patterns before execution.
    Dangerous commands are rejected mechanically. Output is truncated
    to bound context window usage.

    Args:
        command: Shell command string to execute.
        timeout: Maximum execution time in seconds. Default 30, hard cap 300.
        cwd: Working directory for the command. None = current directory.

    Returns:
        CommandResult with command, exit_code, stdout, stderr, duration_ms,
        timed_out flag, and blocked flag.

    See: FORGE_ARCHITECTURE_v0.2.md §11.1
    """
    import subprocess
    import time

    if timeout < 1:
        raise ValueError(f"timeout must be >= 1, got {timeout}")
    timeout = min(timeout, 300)

    blocked_reason = _is_command_blocked(command)
    if blocked_reason is not None:
        return CommandResult(
            command=command,
            exit_code=-1,
            stdout="",
            stderr=blocked_reason,
            duration_ms=0,
            timed_out=False,
            blocked=True,
        )

    start = time.monotonic()
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return CommandResult(
            command=command,
            exit_code=result.returncode,
            stdout=result.stdout[:5000],
            stderr=result.stderr[:2000],
            duration_ms=elapsed_ms,
            timed_out=False,
            blocked=False,
        )
    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return CommandResult(
            command=command,
            exit_code=-1,
            stdout="",
            stderr=f"Command timed out after {timeout} seconds",
            duration_ms=elapsed_ms,
            timed_out=True,
            blocked=False,
        )


def run_tests(
    test_path: str = "",
    timeout: int = 120,
    cwd: str | None = None,
) -> TestResult:
    """Execute the project test suite (or specific test file/function).

    Runs pytest and parses structured output. Captures pass/fail counts
    and error details so the worker can directly act on failures.

    Args:
        test_path: Specific test file or function. Empty string = full suite.
        timeout: Maximum execution time in seconds. Default 120, hard cap 600.
        cwd: Working directory. None = current directory.

    Returns:
        TestResult with test_path, status, counts, duration_ms, failures, timed_out.

    See: FORGE_ARCHITECTURE_v0.2.md §11.1
    """
    import subprocess
    import time

    timeout = min(timeout, 600)

    # Build pytest command with JSON report for structured output
    cmd = ["python", "-m", "pytest", "--tb=short", "-q"]
    if test_path:
        cmd.append(test_path)

    # Check if test path exists (when specified)
    if test_path and not Path(test_path).exists():
        return TestResult(
            test_path=test_path,
            status="error",
            passed=0,
            failed=0,
            errors=0,
            skipped=0,
            duration_ms=0,
            failures=[{
                "test_name": "",
                "message": f"Test path not found: {test_path}",
                "file": test_path,
                "line": 0,
            }],
        )

    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return TestResult(
            test_path=test_path or ".",
            status="error",
            passed=0,
            failed=0,
            errors=0,
            skipped=0,
            duration_ms=elapsed_ms,
            timed_out=True,
        )

    # Parse pytest output — strip ANSI codes first for reliable matching
    import re

    raw_output = result.stdout + result.stderr
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    output = ansi_escape.sub("", raw_output)

    passed = failed = errors = skipped = 0

    summary_match = re.search(r"(\d+) passed", output)
    if summary_match:
        passed = int(summary_match.group(1))

    fail_match = re.search(r"(\d+) failed", output)
    if fail_match:
        failed = int(fail_match.group(1))

    err_match = re.search(r"(\d+) error", output)
    if err_match:
        errors = int(err_match.group(1))

    skip_match = re.search(r"(\d+) skipped", output)
    if skip_match:
        skipped = int(skip_match.group(1))

    # Parse failure details from short traceback summary
    failures: list[dict[str, Any]] = []
    fail_blocks = re.findall(
        r"FAILED\s+(\S+?)(?:\s+-\s+(.+))?$",
        output,
        re.MULTILINE,
    )
    for test_name, message in fail_blocks:
        failures.append({
            "test_name": test_name,
            "message": message or "Test failed",
            "file": test_name.split("::")[0] if "::" in test_name else "",
            "line": 0,
        })

    status = "pass" if result.returncode == 0 else "fail"
    if errors > 0:
        status = "error"

    return TestResult(
        test_path=test_path or ".",
        status=status,
        passed=passed,
        failed=failed,
        errors=errors,
        skipped=skipped,
        duration_ms=elapsed_ms,
        failures=failures,
    )


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


_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "javascript",
    ".rs": "rust",
    ".go": "go",
    ".rb": "ruby",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
}

_PYTHON_SYMBOL_QUERIES = """
(function_definition
  name: (identifier) @name) @func

(class_definition
  name: (identifier) @name) @cls

(import_statement) @import

(import_from_statement) @import

(assignment
  left: (identifier) @name
  type: (type) @type) @typed_assign
"""

_TS_SYMBOL_QUERIES = """
(function_declaration
  name: (identifier) @name) @func

(class_declaration
  name: (type_identifier) @name) @cls

(import_statement) @import

(export_statement) @export

(lexical_declaration) @decl
"""


def _extract_signature(node: Any, source_bytes: bytes) -> str:
    """Extract a clean signature from a tree-sitter node (no body)."""
    text = node.text.decode("utf-8", errors="replace")
    lines = text.split("\n")
    # For functions/classes, take only the signature line(s) up to the colon/brace
    if node.type in (
        "function_definition", "class_definition",
        "function_declaration", "class_declaration",
        "method_definition",
    ):
        sig_lines = []
        for line in lines:
            sig_lines.append(line)
            stripped = line.rstrip()
            if stripped.endswith(":") or stripped.endswith("{"):
                break
        return "\n".join(sig_lines)
    # For imports and other single-line constructs
    return lines[0] if lines else text


def _get_symbol_kind(node_type: str) -> str:
    """Map tree-sitter node type to a symbol kind."""
    mapping = {
        "function_definition": "function",
        "function_declaration": "function",
        "method_definition": "method",
        "class_definition": "class",
        "class_declaration": "class",
        "import_statement": "import",
        "import_from_statement": "import",
        "export_statement": "export",
        "lexical_declaration": "variable",
        "assignment": "variable",
        "typed_assign": "variable",
    }
    return mapping.get(node_type, "other")


def _extract_python_symbols(
    root: Any, source_bytes: bytes
) -> list[dict[str, Any]]:
    """Walk the Python AST and extract symbols."""
    symbols: list[dict[str, Any]] = []

    def _walk(node: Any, depth: int = 0) -> None:
        if node.type == "function_definition":
            symbols.append({
                "name": _get_child_text(node, "name", source_bytes),
                "kind": "function" if depth == 0 else "method",
                "signature": _extract_signature(node, source_bytes),
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
            })
        elif node.type == "class_definition":
            symbols.append({
                "name": _get_child_text(node, "name", source_bytes),
                "kind": "class",
                "signature": _extract_signature(node, source_bytes),
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
            })
            # Recurse into class body for methods
            for child in node.children:
                if child.type == "block":
                    for sub in child.children:
                        _walk(sub, depth + 1)
            return
        elif node.type in ("import_statement", "import_from_statement"):
            symbols.append({
                "name": node.text.decode("utf-8", errors="replace").strip(),
                "kind": "import",
                "signature": node.text.decode("utf-8", errors="replace").strip(),
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
            })

        if depth == 0:
            for child in node.children:
                _walk(child, depth)

    _walk(root)
    return symbols


def _get_child_text(
    node: Any, field_name: str, source: bytes
) -> str:
    """Get the text of a named child field."""
    for child in node.children:
        if child.type == "identifier" or child.type == "type_identifier":
            return child.text.decode("utf-8", errors="replace")
    return "<unknown>"


def _extract_ts_symbols(
    root: Any, source_bytes: bytes
) -> list[dict[str, Any]]:
    """Walk the TypeScript/JS AST and extract symbols."""
    symbols: list[dict[str, Any]] = []

    for child in root.children:
        if child.type in ("function_declaration", "class_declaration"):
            symbols.append({
                "name": _get_child_text(child, "name", source_bytes),
                "kind": _get_symbol_kind(child.type),
                "signature": _extract_signature(child, source_bytes),
                "start_line": child.start_point[0] + 1,
                "end_line": child.end_point[0] + 1,
            })
        elif child.type == "import_statement":
            symbols.append({
                "name": child.text.decode("utf-8", errors="replace").strip(),
                "kind": "import",
                "signature": child.text.decode(
                    "utf-8", errors="replace"
                ).strip(),
                "start_line": child.start_point[0] + 1,
                "end_line": child.end_point[0] + 1,
            })
        elif child.type == "export_statement":
            symbols.append({
                "name": child.text.decode("utf-8", errors="replace")
                .split("\n")[0]
                .strip(),
                "kind": "export",
                "signature": child.text.decode(
                    "utf-8", errors="replace"
                ).split("\n")[0].strip(),
                "start_line": child.start_point[0] + 1,
                "end_line": child.end_point[0] + 1,
            })

    return symbols


def codemap(paths: list[str] | None = None) -> CodemapResult:
    """Generate tree-sitter structural summary of files.

    Extracts function signatures, class definitions, imports, and
    exports using tree-sitter parsing. Returns signatures only --
    no implementation bodies. 10x token savings vs full file content.

    Args:
        paths: Specific files to map. None = empty (caller must provide paths).

    Returns:
        CodemapResult with per-file signature lists.

    See: FORGE_ARCHITECTURE_v0.2.md §4, §11.1
    """
    try:
        from tree_sitter_languages import get_parser
    except ImportError:
        raise ImportError(
            "tree-sitter-languages is required for codemap.\n"
            "FIX: pip install 'tree-sitter>=0.21,<0.22' 'tree-sitter-languages>=1.10'"
        )

    if paths is None:
        paths = []

    files_result: list[dict[str, Any]] = []

    for file_path_str in paths:
        file_path = Path(file_path_str).resolve()
        if not file_path.is_file():
            continue

        suffix = file_path.suffix.lower()
        lang = _LANGUAGE_MAP.get(suffix)
        if lang is None:
            files_result.append({
                "path": str(file_path),
                "language": "unknown",
                "symbols": [],
            })
            continue

        try:
            parser = get_parser(lang)
        except Exception:
            files_result.append({
                "path": str(file_path),
                "language": lang,
                "symbols": [],
            })
            continue

        source = file_path.read_bytes()
        tree = parser.parse(source)
        root = tree.root_node

        if lang == "python":
            symbols = _extract_python_symbols(root, source)
        elif lang in ("typescript", "tsx", "javascript"):
            symbols = _extract_ts_symbols(root, source)
        else:
            symbols = []

        files_result.append({
            "path": str(file_path),
            "language": lang,
            "symbols": symbols,
        })

    return CodemapResult(files=files_result)


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

"""FORGE Agent-Computer Interface (ACI) — bounded, structured tool layer.

Every ACI tool returns structured JSON. Output is always bounded.
Errors are immediate and actionable. Tools are the same regardless of
which model is using them — the harness normalizes the interface.

See: FORGE_ARCHITECTURE_v0.2.md §11
"""

from forge.aci.tools import (
    CommandResult,
    CreateResult,
    EditResult,
    SearchResult,
    TestResult,
    Tool,
    ToolResult,
    ViewResult,
    create_file,
    edit_file,
    find_file,
    run_command,
    run_tests,
    search_dir,
    search_file,
    tree,
    view_file,
)

__all__ = [
    "Tool",
    "ToolResult",
    "ViewResult",
    "EditResult",
    "SearchResult",
    "CommandResult",
    "TestResult",
    "CreateResult",
    "view_file",
    "edit_file",
    "search_file",
    "run_command",
    "run_tests",
    "create_file",
    "find_file",
    "search_dir",
    "tree",
]

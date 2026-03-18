"""FORGE Layer 1: Mechanical Hooks — real-time enforcement.

Hooks run outside the model — the model cannot override them.
They execute on every relevant tool call with a latency budget
of < 100ms per hook.

Hook types:
  - pre_edit: syntax_check (tree-sitter parse before applying edit)
  - post_edit: auto_format + secret_scan
  - pre_command: allowlist_check (block unapproved commands)
  - post_commit: desloppify_mechanical + architectural_lint

See: FORGE_ARCHITECTURE_v0.2.md §6.1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class HookPhase(Enum):
    """When a hook runs in the tool call lifecycle."""

    PRE_EDIT = "pre_edit"
    POST_EDIT = "post_edit"
    PRE_COMMAND = "pre_command"
    POST_COMMIT = "post_commit"


@dataclass(frozen=True)
class HookResult:
    """Result of a hook execution.

    Hooks return allowed=True to proceed, or allowed=False with
    an actionable error message explaining WHAT, WHY, and HOW to fix.

    See: §6.1 Interface
    """

    allowed: bool
    error: str | None = None
    suggestion: str | None = None

    @classmethod
    def allow(cls) -> HookResult:
        return cls(allowed=True)

    @classmethod
    def reject(cls, error: str, suggestion: str | None = None) -> HookResult:
        return cls(allowed=False, error=error, suggestion=suggestion)


@dataclass
class HookConfig:
    """Configuration for a single hook action.

    Loaded from .forge/hooks.yaml.
    """

    action: str
    description: str
    on_fail: str = "reject"
    error_format: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class HookRunner:
    """Executes Layer 1 mechanical hooks on tool calls.

    Hooks are loaded from .forge/hooks.yaml and run automatically
    on every relevant tool call. The runner is the enforcement
    boundary — the model has no way to bypass it.

    Usage::

        runner = HookRunner(hooks_config_path=Path(".forge/hooks.yaml"))
        result = runner.run_pre_edit(path="src/main.py", content="...")
        if not result.allowed:
            # Reject the edit — do not apply it
            print(result.error)

    See: FORGE_ARCHITECTURE_v0.2.md §6.1
    """

    def __init__(self, hooks_config_path: Path | None = None) -> None:
        """Initialize the hook runner.

        Args:
            hooks_config_path: Path to .forge/hooks.yaml.
                             If None, uses defaults.

        TODO: Load hooks.yaml and parse hook configurations.
        """
        self._config_path = hooks_config_path
        self._hooks: dict[str, list[HookConfig]] = {}

    def load_config(self) -> None:
        """Load hook configurations from .forge/hooks.yaml.

        TODO: Implement YAML loading and validation (§6.1).
        """
        raise NotImplementedError("load_config not yet implemented — see §6.1")

    def run_pre_edit(self, path: str, content: str) -> HookResult:
        """Run pre_edit hooks: syntax check via tree-sitter.

        Parses the file content with tree-sitter before the edit
        is applied. Rejects edits that would introduce syntax errors.

        Args:
            path: File path being edited.
            content: New content to validate.

        Returns:
            HookResult — allowed or rejected with error details.

        TODO: Implement tree-sitter syntax validation (§6.1 pre_edit).
        TODO: Detect language from file extension.
        TODO: Ensure < 100ms latency budget.
        """
        raise NotImplementedError("run_pre_edit not yet implemented — see §6.1")

    def run_post_edit(self, path: str, content: str) -> HookResult:
        """Run post_edit hooks: auto-format + secret scan.

        After a successful edit:
        1. Run formatter (auto-detect from project config)
        2. Scan for hardcoded secrets using regex patterns

        Args:
            path: File path that was edited.
            content: The content after editing.

        Returns:
            HookResult — allowed or rejected (secrets found).

        TODO: Implement auto-format detection (prettier, black, etc.) (§6.1 post_edit).
        TODO: Implement secret scanning with configurable patterns (§6.1 post_edit).
        """
        raise NotImplementedError("run_post_edit not yet implemented — see §6.1")

    def run_pre_command(self, command: str) -> HookResult:
        """Run pre_command hooks: allowlist check.

        Validates the command against allowed/blocked patterns.
        Dangerous commands (rm -rf, sudo, eval, curl|bash) are
        blocked mechanically.

        Args:
            command: Shell command string to validate.

        Returns:
            HookResult — allowed or blocked with error and allowed list.

        TODO: Implement allowlist/blocklist matching (§6.1 pre_command).
        TODO: Load allowed_patterns and blocked_patterns from hooks.yaml.
        """
        raise NotImplementedError("run_pre_command not yet implemented — see §6.1")

    def run_post_commit(self, changed_files: list[str]) -> HookResult:
        """Run post_commit hooks: desloppify + architectural lint.

        After a commit, run:
        1. Desloppify mechanical scan (§6.3)
        2. Architectural linter rules (§6.2)

        Args:
            changed_files: List of files changed in the commit.

        Returns:
            HookResult with combined results.

        TODO: Wire DesloppifyMechanical (§6.3).
        TODO: Wire ArchitecturalLinter (§6.2).
        """
        raise NotImplementedError("run_post_commit not yet implemented — see §6.1")

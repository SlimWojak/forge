"""FORGE Layer 2: Architectural Linters — CI-style enforcement.

Custom linters that encode project-specific structural rules.
Error messages are written for agents — they explain WHY the rule
exists and the CORRECT approach.

Rules are defined in .forge/architecture.yaml and evaluated via
regex matching and tree-sitter AST analysis.

Runs on post_commit hook and as part of CI-style checks before
Oracle generation.

See: FORGE_ARCHITECTURE_v0.2.md §6.2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LintRule:
    """A single architectural linter rule.

    Loaded from .forge/architecture.yaml. Each rule has an
    agent-readable message explaining WHAT, WHY, and HOW TO FIX.

    See: §6.2 for rule schema and examples.
    """

    id: str
    name: str
    severity: str  # "error" | "warning"
    message: str
    files: str = ""  # Glob pattern for files this rule applies to
    pattern: str = ""  # Regex pattern to detect violations
    must_contain: str = ""  # Regex that must be present in matching files
    custom_check: str = ""  # Name of a custom check function
    promoted_from: str | None = None  # Skill ID if promoted from Tier 2


@dataclass
class LintViolation:
    """A single linter violation found in a file."""

    rule_id: str
    file: str
    line: int | None = None
    severity: str = "error"
    message: str = ""
    matched_text: str = ""


@dataclass
class LintResult:
    """Aggregated result of running all architectural linter rules.

    See: §6.2 Interface output spec.
    """

    violations: list[LintViolation] = field(default_factory=list)
    warnings: list[LintViolation] = field(default_factory=list)
    passed: bool = True


class ArchitecturalLinter:
    """Evaluates architectural linter rules against changed files.

    Rules are loaded from .forge/architecture.yaml and include:
    - Regex pattern rules (import checks, secret detection)
    - Must-contain rules (error boundaries required)
    - Custom check functions (test file naming conventions)

    Error messages are agent-readable: WHAT + WHY + HOW TO FIX.

    Usage::

        linter = ArchitecturalLinter(
            rules_path=Path(".forge/architecture.yaml")
        )
        result = linter.check(changed_files=["src/api/auth.ts"])

    See: FORGE_ARCHITECTURE_v0.2.md §6.2
    """

    def __init__(self, rules_path: Path | None = None) -> None:
        """Initialize the linter with rules from architecture.yaml.

        Args:
            rules_path: Path to .forge/architecture.yaml.
        """
        self._rules_path = rules_path
        self._rules: list[LintRule] = []
        self._sensitive_paths: list[str] = []

    def load_rules(self) -> None:
        """Load rules from .forge/architecture.yaml.

        TODO: Implement YAML loading and rule parsing (§6.2).
        TODO: Load sensitive_paths list.
        """
        raise NotImplementedError("load_rules not yet implemented — see §6.2")

    def check(
        self,
        changed_files: list[str],
        project_root: Path | None = None,
    ) -> LintResult:
        """Run all linter rules against the given files.

        Evaluates each rule that matches the file patterns, checking
        for regex violations and must-contain requirements.

        Args:
            changed_files: List of changed file paths to check.
            project_root: Project root for resolving file paths.

        Returns:
            LintResult with violations, warnings, and pass/fail.

        TODO: Implement rule evaluation engine (§6.2).
        TODO: Support regex pattern matching.
        TODO: Support must_contain checks.
        TODO: Support tree-sitter AST analysis for custom checks.
        """
        raise NotImplementedError("check not yet implemented — see §6.2")

    def add_rule(self, rule: LintRule) -> None:
        """Add a new rule (used by Tier 3 skill promotion).

        When a skill is promoted to Tier 3, it becomes an
        architectural linter rule appended to architecture.yaml.

        See: §9.2 Tier 3 schema, §9.3 Promotion Logic.

        TODO: Implement rule addition and persistence.
        """
        raise NotImplementedError("add_rule not yet implemented — see §9.2")

    def is_sensitive_path(self, path: str) -> bool:
        """Check if a file path matches a sensitive path pattern.

        Sensitive paths (auth, payments, config, migrations) trigger
        higher review intensity in the Gate Engine.

        Args:
            path: File path to check.

        Returns:
            True if the path matches a sensitive pattern.

        TODO: Implement glob matching against sensitive_paths (§6.2).
        """
        raise NotImplementedError("is_sensitive_path not yet implemented — see §6.2")

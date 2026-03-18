"""FORGE Layer 3: Desloppify — dual quality enforcement.

Two architecturally distinct quality systems:

L3a — DesloppifyMechanical (continuous, zero-GPU):
  Tree-sitter based detectors for dead code, duplication,
  cyclomatic complexity, function length, nesting depth.
  Runs in hooks on every commit. < 2 seconds latency.

L3b — DesloppifySubjective (milestone-gated, LLM):
  Assesses naming quality, abstraction boundaries, module cohesion,
  pattern consistency, API design. Runs at milestone boundaries
  when GPU is not serving workers.

See: FORGE_ARCHITECTURE_v0.2.md §6.3, §6.4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------


@dataclass
class QualityIssue:
    """A single quality issue detected by Desloppify."""

    file: str
    issue_type: str  # "dead_code" | "duplication" | "complexity" | "length" | "nesting"
    detail: str
    line: int | None = None
    function: str | None = None
    severity: str = "warning"  # "error" | "warning" | "suggestion"


@dataclass
class MechanicalScanResult:
    """Result of a Desloppify mechanical scan.

    See: §6.3 Interface output spec.
    """

    score: int  # 0-100, clamped
    delta: str  # e.g., "+3", "-2"
    issues: list[QualityIssue] = field(default_factory=list)
    resolved: list[QualityIssue] = field(default_factory=list)


@dataclass
class SubjectiveIssue:
    """A single subjective quality issue from LLM review."""

    category: str  # "naming" | "abstraction" | "cohesion" | "consistency" | "api_design"
    file: str
    detail: str
    severity: str = "suggestion"  # "blocking" | "recommendation" | "suggestion"
    effort: str = "trivial"  # "trivial" | "moderate" | "significant"


@dataclass
class SubjectiveScanResult:
    """Result of a Desloppify subjective scan.

    See: §6.4 Output schema.
    """

    score: int
    delta_from_previous: str
    scan_scope: str
    issues: list[SubjectiveIssue] = field(default_factory=list)
    model_used: str = ""
    tokens_consumed: int = 0
    timestamp: str = ""


# ---------------------------------------------------------------------------
# L3a: Desloppify Mechanical
# ---------------------------------------------------------------------------


class DesloppifyMechanical:
    """Tree-sitter-based quality detection — zero-GPU, continuous.

    Detectors (§6.3):
      - Dead code: unreferenced functions, unused imports, unreachable branches
      - Duplication: AST subtree similarity hashing (min 6 statements)
      - Cyclomatic complexity: decision points per function (threshold: 10)
      - Function length: line count per function body (threshold: 50)
      - Nesting depth: max indent level (threshold: 4)

    Score formula:
      score = 100 - (dead_code*1 + duplication*2 + complexity*3 +
                      length*2 + nesting*2)
      Clamped to [0, 100].

    Usage::

        scanner = DesloppifyMechanical(config=enforcement_config)
        result = scanner.scan(changed_files=["src/api/auth.py"])

    See: FORGE_ARCHITECTURE_v0.2.md §6.3
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize with thresholds from config.

        Args:
            config: Enforcement config from .forge/config.yaml §13.1.
        """
        config = config or {}
        thresholds = config.get("thresholds", {})
        self._dead_code_max = thresholds.get("dead_code_max", 5)
        self._duplication_max = thresholds.get("duplication_max", 3)
        self._complexity_max = thresholds.get("complexity_max", 10)
        self._function_length_max = thresholds.get("function_length_max", 50)
        self._nesting_depth_max = thresholds.get("nesting_depth_max", 4)

    def scan(
        self,
        changed_files: list[str],
        project_root: Path | None = None,
    ) -> MechanicalScanResult:
        """Run all mechanical quality detectors on the given files.

        Target latency: < 2 seconds for a typical commit.

        Args:
            changed_files: Files to scan (or all files for `forge quality`).
            project_root: Project root for resolving paths.

        Returns:
            MechanicalScanResult with score, delta, and issues.

        TODO: Implement tree-sitter parsing for each detector (§6.3).
        TODO: Implement score computation with weights.
        TODO: Compute delta from previous scan.
        """
        raise NotImplementedError("scan not yet implemented — see §6.3")

    def detect_dead_code(self, file_path: str) -> list[QualityIssue]:
        """Detect unreferenced functions, unused imports, unreachable branches.

        Uses tree-sitter AST to find:
        - Functions defined but never called within the file
        - Import statements not referenced in the file body
        - Branches after return/raise/break statements

        TODO: Implement tree-sitter dead code detection (§6.3).
        """
        raise NotImplementedError("detect_dead_code not yet implemented — see §6.3")

    def detect_duplication(
        self,
        file_paths: list[str],
    ) -> list[QualityIssue]:
        """Detect code duplication via AST subtree similarity hashing.

        Minimum threshold: 6 statements for a duplication match.

        TODO: Implement AST similarity hashing (§6.3).
        """
        raise NotImplementedError("detect_duplication not yet implemented — see §6.3")

    def detect_complexity(self, file_path: str) -> list[QualityIssue]:
        """Detect functions exceeding cyclomatic complexity threshold.

        Counts decision points (if, elif, for, while, try, and, or)
        per function using tree-sitter.

        TODO: Implement complexity counting (§6.3).
        """
        raise NotImplementedError("detect_complexity not yet implemented — see §6.3")

    def detect_function_length(self, file_path: str) -> list[QualityIssue]:
        """Detect functions exceeding the line count threshold.

        TODO: Implement function body line counting (§6.3).
        """
        raise NotImplementedError(
            "detect_function_length not yet implemented — see §6.3"
        )

    def detect_nesting_depth(self, file_path: str) -> list[QualityIssue]:
        """Detect functions exceeding the max nesting depth.

        TODO: Implement nesting depth measurement (§6.3).
        """
        raise NotImplementedError(
            "detect_nesting_depth not yet implemented — see §6.3"
        )

    def compute_score(self, issues: list[QualityIssue]) -> int:
        """Compute the mechanical quality score from issues.

        Formula (§6.3):
          score = 100 - (dead_code*1 + duplication*2 + complexity*3 +
                          length*2 + nesting*2)
          Clamped to [0, 100].

        Args:
            issues: List of detected quality issues.

        Returns:
            Quality score (0-100).
        """
        weights = {
            "dead_code": 1,
            "duplication": 2,
            "complexity": 3,
            "length": 2,
            "nesting": 2,
        }
        penalty = sum(weights.get(i.issue_type, 1) for i in issues)
        return max(0, min(100, 100 - penalty))


# ---------------------------------------------------------------------------
# L3b: Desloppify Subjective
# ---------------------------------------------------------------------------


class DesloppifySubjective:
    """LLM-dependent quality review — runs at milestone boundaries.

    Assesses (§6.4):
      - Naming quality: descriptive, consistent names
      - Abstraction boundaries: right code in right module
      - Module cohesion: each module does one thing
      - Pattern consistency: new code matches established patterns
      - API design quality: clean, predictable interfaces

    Scheduling:
      - Runs when GPU is not serving workers (milestone boundary)
      - Uses the planner model or dedicated quality model
      - Receives: full codemap + changed files since last scan

    Gate interaction:
      - Score below threshold (default 60) blocks milestone advancement
      - Worker receives issues as TODO items

    Usage::

        scanner = DesloppifySubjective(config=enforcement_config)
        result = scanner.scan(
            codemap=full_codemap,
            changed_files=changed_since_last_scan,
            scope="milestone-001",
        )

    See: FORGE_ARCHITECTURE_v0.2.md §6.4
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize with config.

        Args:
            config: Enforcement config from .forge/config.yaml §13.1.
        """
        config = config or {}
        subjective = config.get("subjective", {})
        self._min_score = subjective.get("min_score_to_advance", 60)
        self._model = subjective.get("model", "planner")

    def scan(
        self,
        codemap: dict[str, Any],
        changed_files: list[str],
        scope: str = "",
    ) -> SubjectiveScanResult:
        """Run subjective quality review via LLM.

        Sends codemap and changed files to the quality model for
        assessment of naming, abstraction, cohesion, consistency,
        and API design.

        Args:
            codemap: Full project codemap (tree-sitter signatures).
            changed_files: Files changed since last subjective scan.
            scope: Scope label (e.g., "milestone-001").

        Returns:
            SubjectiveScanResult with score, issues, and metadata.

        TODO: Implement LLM-based quality review (§6.4).
        TODO: Format codemap for model consumption.
        TODO: Parse structured LLM output into SubjectiveIssue list.
        """
        raise NotImplementedError("scan not yet implemented — see §6.4")

    def should_block_milestone(self, score: int) -> bool:
        """Check if the subjective score blocks milestone advancement.

        Args:
            score: Current subjective quality score.

        Returns:
            True if score is below the configured threshold.
        """
        return score < self._min_score

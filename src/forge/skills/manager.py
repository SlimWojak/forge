"""FORGE Skill Manager — crystallization pipeline management.

Manages the lifecycle of learned patterns through the skill tiers.
Handles skill creation, promotion, injection into worker prompts,
and persistence to .forge/skills/.

Promotion thresholds (§9.3):
  Tier 0 → 1: Same pattern observed N times (default N=2)
  Tier 1 → 2: Applied M times successfully (default M=5)
  Tier 2 → 3: Stable for P applications (default P=10) + expressible as structural check
  Tier 3 → 4: Phase 2+ (generated tests)
  Tier 4 → 5: Phase 2+ (LoRA weights)

See: FORGE_ARCHITECTURE_v0.2.md §9
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any


class SkillTier(IntEnum):
    """Skill crystallization tiers.

    Each tier represents a different level of hardening, from
    soft (prompt injection) to hard (model weights).

    See: §9.1 Pipeline Overview
    """

    OBSERVATION = 0
    PROMPT = 1
    YAML_PATTERN = 2
    LINTER_RULE = 3
    GENERATED_TEST = 4  # Phase 2+
    LORA = 5  # Phase 2+


@dataclass
class SkillApplicability:
    """When a skill should be activated.

    Skills are matched against task description and file paths
    to determine relevance.

    See: §9.2 Tier schemas
    """

    file_patterns: list[str] = field(default_factory=list)
    task_keywords: list[str] = field(default_factory=list)


@dataclass
class Skill:
    """A learned pattern at any tier of the crystallization pipeline.

    Skills are created from observations (reviewer feedback) and
    promoted downward through tiers as confidence increases.

    See: §9.2 Tier Schemas
    """

    id: str
    tier: SkillTier
    name: str
    content: str
    confidence: float = 0.0
    applications: int = 0
    successes: int = 0
    learned_from: str = ""  # verdict ID that spawned this skill
    promoted_from: str | None = None  # skill ID of predecessor
    created_at: str = ""
    applicable_when: SkillApplicability = field(default_factory=SkillApplicability)

    # Tier 2 additions
    examples: list[dict[str, str]] = field(default_factory=list)
    counter_examples: list[dict[str, str]] = field(default_factory=list)

    def to_yaml(self) -> dict[str, Any]:
        """Serialize skill to YAML-compatible dict for persistence."""
        # TODO: Implement serialization matching §9.2 tier schemas
        raise NotImplementedError("Skill.to_yaml not yet implemented")

    @classmethod
    def from_yaml(cls, data: dict[str, Any]) -> Skill:
        """Deserialize skill from YAML dict."""
        # TODO: Implement deserialization
        raise NotImplementedError("Skill.from_yaml not yet implemented")


class SkillManager:
    """Manages the skill crystallization pipeline.

    Handles skill creation, promotion, injection, and persistence.

    Usage::

        manager = SkillManager(project_root=Path("."))
        manager.load_skills()

        # Create a skill from a reviewer observation
        manager.create_from_observation(
            verdict_id="verdict-015",
            pattern="Missing rate limit on auth endpoint",
            file_patterns=["src/api/auth/**"],
        )

        # Get relevant skills for a task
        skills = manager.match_skills(
            task_description="Implement login endpoint",
            file_paths=["src/api/auth/login.py"],
        )

        # Inject skills into worker system prompt
        prompt_addition = manager.format_for_injection(skills)

    See: FORGE_ARCHITECTURE_v0.2.md §9
    """

    def __init__(
        self,
        project_root: Path,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the skill manager.

        Args:
            project_root: Project root directory.
            config: Skills section from .forge/config.yaml.
        """
        self._project_root = project_root
        config = config or {}
        self._prompts_dir = project_root / config.get(
            "prompts_dir", ".forge/skills/prompts"
        )
        self._patterns_dir = project_root / config.get(
            "patterns_dir", ".forge/skills/patterns"
        )
        self._max_injected = config.get("max_injected_skills", 5)
        self._max_injection_tokens = config.get("max_injection_tokens", 500)
        self._promotion_config = config.get("promotion", {})
        self._skills: list[Skill] = []

    def load_skills(self) -> None:
        """Load all skills from .forge/skills/ directories.

        Reads Tier 1 prompts from .forge/skills/prompts/
        and Tier 2 patterns from .forge/skills/patterns/.

        TODO: Implement YAML loading from both directories (§9.2).
        """
        raise NotImplementedError("load_skills not yet implemented — see §9.2")

    def create_from_observation(
        self,
        verdict_id: str,
        pattern: str,
        file_patterns: list[str] | None = None,
        task_keywords: list[str] | None = None,
    ) -> Skill | None:
        """Create a Tier 1 prompt skill from a reviewer observation.

        Tier 0 → Tier 1 promotion: triggers when the same pattern
        is observed N times (default N=2). First observation is
        stored as Tier 0; on Nth observation, promotes to Tier 1.

        Args:
            verdict_id: The verdict that contains this observation.
            pattern: The learned pattern text.
            file_patterns: File path patterns for applicability.
            task_keywords: Task keywords for applicability.

        Returns:
            New Skill if promoted to Tier 1, None if still observing.

        See: §9.3 Promotion Logic (Tier 0 → Tier 1)

        TODO: Implement observation tracking and promotion (§9.3).
        TODO: Write new skill to .forge/skills/prompts/.
        TODO: Record skill_event in observability pipeline.
        """
        raise NotImplementedError(
            "create_from_observation not yet implemented — see §9.3"
        )

    def promote(self, skill_id: str) -> Skill | None:
        """Promote a skill to the next tier.

        Tier 1 → 2: Applied M times successfully (default M=5).
        Tier 2 → 3: Stable for P applications (default P=10)
                     AND expressible as structural check.
        Tier 3+ → Phase 2+

        Args:
            skill_id: ID of the skill to promote.

        Returns:
            Updated Skill if promotion succeeded, None if not eligible.

        See: §9.3 Promotion Logic

        TODO: Implement promotion logic with threshold checks (§9.3).
        TODO: For Tier 2 → 3: generate linter rule and add to architecture.yaml.
        TODO: Record promotion event in observability pipeline.
        """
        raise NotImplementedError("promote not yet implemented — see §9.3")

    def match_skills(
        self,
        task_description: str,
        file_paths: list[str] | None = None,
    ) -> list[Skill]:
        """Find relevant skills for a task.

        Matches task description and file paths against all Tier 1
        and Tier 2 skills. Returns up to max_injected_skills matches,
        ordered by confidence.

        Args:
            task_description: Description of the task.
            file_paths: File paths the task may touch.

        Returns:
            List of matching skills, ordered by confidence.

        See: §9.4 Skill Injection

        TODO: Implement keyword and glob matching (§9.4).
        TODO: Order by confidence, cap at max_injected_skills.
        """
        raise NotImplementedError("match_skills not yet implemented — see §9.4")

    def format_for_injection(self, skills: list[Skill]) -> str:
        """Format matched skills for injection into worker system prompt.

        Concatenates skill content, respecting the max_injection_tokens
        budget. Skills are ordered by confidence.

        Args:
            skills: Skills to inject (from match_skills).

        Returns:
            Formatted string for system prompt injection.

        See: §9.4 Skill Injection

        TODO: Implement token-aware concatenation (§9.4).
        """
        raise NotImplementedError(
            "format_for_injection not yet implemented — see §9.4"
        )

    def record_application(
        self,
        skill_id: str,
        task_id: str,
        success: bool,
    ) -> None:
        """Record that a skill was applied to a task.

        Updates the skill's application and success counts.
        Used to determine promotion eligibility.

        Args:
            skill_id: The skill that was applied.
            task_id: The task it was applied to.
            success: Whether the task passed review without the skill's error recurring.

        TODO: Update skill state and persist (§9.3).
        TODO: Record skill_event in observability pipeline.
        """
        raise NotImplementedError(
            "record_application not yet implemented — see §9.3"
        )

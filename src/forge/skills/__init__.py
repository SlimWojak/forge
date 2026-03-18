"""FORGE Skills — crystallization pipeline from soft to hard.

Skills crystallize downward through tiers:
  Tier 0: Observation (raw event data)
  Tier 1: Prompt skill (injected into worker system prompt)
  Tier 2: YAML pattern (structured rule with examples)
  Tier 3: Architectural linter rule (tree-sitter/regex enforcement)
  Tier 4: Generated test (Phase 2+)
  Tier 5: LoRA weight (Phase 2+)

Phase 1 scope: Tiers 1-3.

See: FORGE_ARCHITECTURE_v0.2.md §9
"""

from forge.skills.manager import Skill, SkillManager, SkillTier

__all__ = ["Skill", "SkillManager", "SkillTier"]

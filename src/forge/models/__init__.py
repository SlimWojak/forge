"""FORGE Model Interface — abstracts local and frontier model access.

Provides a unified OpenAI-compatible API interface for all model
interactions, with role-based routing to the correct endpoint.

Roles:
  - planner: Mission decomposition, milestone planning (DGX Spark #1)
  - worker: Code generation, test writing (DGX Spark #2)
  - reviewer: Primary frontier reviewer (Anthropic/OpenAI)
  - escalation_reviewer: Second reviewer on failure escalation
  - chairman: Verdict synthesis (Phase 2+, Opus)
  - intelligence: Research/web intel (Grok, not code review)
  - quality: Desloppify subjective review

See: FORGE_ARCHITECTURE_v0.2.md §13.1 models section
"""

from forge.models.provider import ModelProvider, ModelRole

__all__ = ["ModelProvider", "ModelRole"]

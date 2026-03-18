"""FORGE Oracle — structured snapshot mediating frontier review.

The Oracle is a two-tier system:
- Tier 1 (Core Oracle): ~2-4K tokens sent to all reviewers
- Tier 2 (Annexes): Expandable sections pulled on demand

Frontier models never see the full codebase. They see the Oracle.
Built on a custom tree-sitter pipeline, not RepoPrompt-dependent.

See: FORGE_ARCHITECTURE_v0.2.md §4
"""

from forge.oracle.generator import (
    AnnexType,
    CoreOracle,
    DiffSummary,
    OracleGenerator,
    OracleMetadata,
)

__all__ = [
    "AnnexType",
    "CoreOracle",
    "DiffSummary",
    "OracleGenerator",
    "OracleMetadata",
]

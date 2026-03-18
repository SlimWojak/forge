"""FORGE Enforcement Layer — three architecturally distinct systems.

L1: Mechanical Hooks (real-time) — runs on every tool call
L2: Architectural Linters (CI-style) — runs on every commit
L3a: Desloppify Mechanical (continuous) — tree-sitter, zero-GPU
L3b: Desloppify Subjective (milestone-gated) — LLM-dependent

The model cannot override the enforcement layer. Hooks run outside
the model and reject operations mechanically.

See: FORGE_ARCHITECTURE_v0.2.md §6
"""

from forge.enforcement.hooks import HookResult, HookRunner
from forge.enforcement.linters import ArchitecturalLinter, LintViolation
from forge.enforcement.quality import DesloppifyMechanical, DesloppifySubjective

__all__ = [
    "HookRunner",
    "HookResult",
    "ArchitecturalLinter",
    "LintViolation",
    "DesloppifyMechanical",
    "DesloppifySubjective",
]

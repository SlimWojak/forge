"""FORGE Config Loader — reads .forge/config.yaml.

Simple YAML loader that returns typed dicts for model configs.
No classes, no validation beyond existence — YAGNI for Phase 1.5.

See: FORGE_ARCHITECTURE_v0.2.md §13.1
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(project_root: Path | str) -> dict[str, Any]:
    """Load .forge/config.yaml from the project root.

    Args:
        project_root: Path to the project directory containing .forge/

    Returns:
        Parsed config dict.

    Raises:
        FileNotFoundError: If config.yaml does not exist.
    """
    root = Path(project_root)
    config_path = root / ".forge" / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_model_config(config: dict[str, Any], role: str) -> dict[str, Any]:
    """Get model configuration for a given role name.

    Looks up the role in models.local first, then models.frontier.

    Args:
        config: Full config dict from load_config().
        role: Role name (worker, planner, reviewer, escalation_reviewer, etc.)

    Returns:
        Dict with model config (endpoint, model, temperature, etc.)

    Raises:
        KeyError: If role not found in any model section.
    """
    models = config.get("models", {})

    # Check local models
    local = models.get("local", {})
    if role in local:
        return local[role]

    # Check frontier models
    frontier = models.get("frontier", {})
    if role in frontier:
        return frontier[role]

    raise KeyError(f"No model configured for role: {role}")

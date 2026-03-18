"""Protocol adapter bridging ModelProvider to ModelInterface/ReviewerModel.

The worker (aci/worker.py) and gate (gate/engine.py) expect objects
with a chat_completion(messages, tools) -> dict method returning
raw OpenAI-format dicts. ModelProvider.complete() returns a
CompletionResponse dataclass. This adapter bridges the gap.

Usage:
    provider = ModelProvider(config=cfg)
    worker_model = LocalModelAdapter(provider, role="worker")
    reviewer_model = LocalModelAdapter(provider, role="reviewer")

    # Now pass to existing code:
    run_worker(task, model=worker_model)
    GateEngine(reviewer=reviewer_model)
"""
from __future__ import annotations

from typing import Any

from forge.models.provider import ModelProvider


class LocalModelAdapter:
    """Thin adapter: ModelProvider -> ModelInterface/ReviewerModel protocol."""

    def __init__(self, provider: ModelProvider, role: str) -> None:
        self._provider = provider
        self._role = role

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Return raw OpenAI-format response dict."""
        return self._provider.raw_chat_completion(
            role=self._role,
            messages=messages,
            tools=tools,
        )

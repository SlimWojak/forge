"""FORGE Model Provider — unified interface for local + frontier models.

Abstracts the differences between local vLLM endpoints and frontier
API providers behind a single OpenAI-compatible interface. Routes
requests to the correct endpoint based on model role.

See: FORGE_ARCHITECTURE_v0.2.md §13.1 models section
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx


class ModelRole(Enum):
    """Roles that models serve in the FORGE system."""

    PLANNER = "planner"
    WORKER = "worker"
    REVIEWER = "reviewer"
    ESCALATION_REVIEWER = "escalation_reviewer"
    CHAIRMAN = "chairman"
    INTELLIGENCE = "intelligence"
    QUALITY = "quality"


@dataclass
class ModelConfig:
    """Configuration for a single model endpoint."""

    model: str
    endpoint: str = ""
    provider: str = "local"
    api_key_env: str = ""
    role: str = ""
    max_tokens: int = 4096
    temperature: float = 0.2
    lora_path: str | None = None


@dataclass
class CompletionRequest:
    """A request to a model for text completion."""

    messages: list[dict[str, str]]
    max_tokens: int = 4096
    temperature: float = 0.2
    system_prompt: str | None = None
    response_format: str | None = None


@dataclass
class CompletionResponse:
    """Response from a model completion."""

    content: str
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    cost_usd: float | None = None
    finish_reason: str = "stop"


class ModelProvider:
    """Unified interface for all model interactions.

    Routes requests to the correct endpoint based on role.
    Supports local vLLM (OpenAI-compatible) endpoints.

    See: FORGE_ARCHITECTURE_v0.2.md §13.1
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._models: dict[str, ModelConfig] = {}
        self._parse_config()

    def _parse_config(self) -> None:
        """Parse model configs from the config dict."""
        models = self._config.get("models", {})
        for section in ("local", "frontier"):
            for role, cfg in models.get(section, {}).items():
                self._models[role] = ModelConfig(
                    model=cfg.get("model", ""),
                    endpoint=cfg.get("endpoint", ""),
                    provider=(
                        "local" if section == "local"
                        else cfg.get("provider", "")
                    ),
                    api_key_env=cfg.get("api_key_env", ""),
                    role=cfg.get("role", role),
                    max_tokens=cfg.get("max_tokens", 4096),
                    temperature=cfg.get("temperature", 0.2),
                )

    def get_model_config(self, role: ModelRole | str) -> ModelConfig:
        """Get the model configuration for a given role."""
        role_str = role.value if isinstance(role, ModelRole) else role
        if role_str not in self._models:
            raise KeyError(f"No model configured for role: {role_str}")
        return self._models[role_str]

    def complete(
        self,
        role: ModelRole | str,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
        response_format: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> CompletionResponse:
        """Send a completion request to the model for the given role."""
        config = self.get_model_config(role)
        request = CompletionRequest(
            messages=messages,
            max_tokens=max_tokens or config.max_tokens,
            temperature=temperature if temperature is not None else config.temperature,
            system_prompt=system_prompt,
            response_format=response_format,
        )
        if config.provider == "local":
            return self._call_local(config, request, tools=tools)
        raise NotImplementedError(
            f"Provider {config.provider!r} not yet implemented"
        )

    def raw_chat_completion(
        self,
        role: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Return raw OpenAI-format response dict. Used by adapter."""
        config = self.get_model_config(role)
        body: dict[str, Any] = {
            "model": config.model,
            "messages": messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        # Suppress thinking tokens for Qwen3.5
        body["chat_template_kwargs"] = {"enable_thinking": False}

        url = f"{config.endpoint}/chat/completions"
        resp = httpx.post(url, json=body, timeout=300.0)
        resp.raise_for_status()
        return resp.json()

    def _call_local(
        self,
        config: ModelConfig,
        request: CompletionRequest,
        tools: list[dict[str, Any]] | None = None,
    ) -> CompletionResponse:
        """Call a local vLLM endpoint (OpenAI-compatible API)."""
        body: dict[str, Any] = {
            "model": config.model,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        # Suppress thinking tokens for Qwen3.5
        body["chat_template_kwargs"] = {"enable_thinking": False}

        url = f"{config.endpoint}/chat/completions"
        start = time.monotonic()
        resp = httpx.post(url, json=body, timeout=300.0)
        resp.raise_for_status()
        elapsed = int((time.monotonic() - start) * 1000)

        data = resp.json()
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = data.get("usage", {})

        content = message.get("content") or ""
        return CompletionResponse(
            content=content,
            model=config.model,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            latency_ms=elapsed,
            finish_reason=choice.get("finish_reason", "stop"),
        )

    def _call_anthropic(
        self,
        config: ModelConfig,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Call the Anthropic API for Claude models. Phase 2+."""
        raise NotImplementedError("_call_anthropic not yet implemented")

    def _call_openai(
        self,
        config: ModelConfig,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Call the OpenAI API for GPT models. Phase 2+."""
        raise NotImplementedError("_call_openai not yet implemented")

    def _call_xai(
        self,
        config: ModelConfig,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Call the xAI API for Grok models. Phase 2+."""
        raise NotImplementedError("_call_xai not yet implemented")

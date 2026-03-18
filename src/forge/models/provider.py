"""FORGE Model Provider — unified interface for local + frontier models.

Abstracts the differences between local vLLM endpoints and frontier
API providers behind a single OpenAI-compatible interface. Routes
requests to the correct endpoint based on model role.

See: FORGE_ARCHITECTURE_v0.2.md §13.1 models section
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ModelRole(Enum):
    """Roles that models serve in the FORGE system.

    Each role maps to a specific model endpoint in config.
    """

    PLANNER = "planner"
    WORKER = "worker"
    REVIEWER = "reviewer"
    ESCALATION_REVIEWER = "escalation_reviewer"
    CHAIRMAN = "chairman"  # Phase 2+
    INTELLIGENCE = "intelligence"  # Optional, Grok
    QUALITY = "quality"  # Desloppify subjective


@dataclass
class ModelConfig:
    """Configuration for a single model endpoint.

    Matches the config schema in §13.1.
    """

    model: str
    endpoint: str = ""  # For local models (vLLM)
    provider: str = "local"  # "local" | "anthropic" | "openai" | "xai"
    api_key_env: str = ""  # Environment variable name for API key
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
    response_format: str | None = None  # "json" for structured output


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
    Supports both local vLLM (OpenAI-compatible) and frontier
    APIs (Anthropic, OpenAI, xAI).

    Usage::

        provider = ModelProvider(config=models_config)

        # Use the worker model
        response = provider.complete(
            role=ModelRole.WORKER,
            messages=[{"role": "user", "content": "Implement..."}],
        )

        # Use the reviewer model
        verdict = provider.complete(
            role=ModelRole.REVIEWER,
            messages=[{"role": "user", "content": oracle_json}],
        )

    See: FORGE_ARCHITECTURE_v0.2.md §13.1
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize with model configurations from .forge/config.yaml.

        Args:
            config: The models section from config.yaml.
                    Contains 'local' and 'frontier' subsections.

        TODO: Parse model configurations from config (§13.1).
        TODO: Validate API key environment variables.
        """
        self._config = config or {}
        self._models: dict[ModelRole, ModelConfig] = {}

    def get_model_config(self, role: ModelRole) -> ModelConfig:
        """Get the model configuration for a given role.

        Args:
            role: The model role to look up.

        Returns:
            ModelConfig for the role.

        Raises:
            KeyError: If no model is configured for the role.

        TODO: Implement config lookup (§13.1).
        """
        raise NotImplementedError("get_model_config not yet implemented — see §13.1")

    def complete(
        self,
        role: ModelRole,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
        response_format: str | None = None,
    ) -> CompletionResponse:
        """Send a completion request to the model for the given role.

        Routes to the correct endpoint (local vLLM or frontier API)
        based on the role's configuration.

        Args:
            role: Which model role to use.
            messages: Chat messages in OpenAI format.
            max_tokens: Override max tokens from config.
            temperature: Override temperature from config.
            system_prompt: System prompt to prepend.
            response_format: "json" for structured output.

        Returns:
            CompletionResponse with content and usage metadata.

        TODO: Implement OpenAI-compatible API call for local models (§13.1).
        TODO: Implement Anthropic API call for Claude models.
        TODO: Implement OpenAI API call for GPT models.
        TODO: Implement xAI API call for Grok models.
        TODO: Record model call in observability pipeline (§10.2).
        """
        raise NotImplementedError("complete not yet implemented — see §13.1")

    def _call_local(
        self,
        config: ModelConfig,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Call a local vLLM endpoint (OpenAI-compatible API).

        Uses httpx to POST to the local vLLM /v1/chat/completions endpoint.

        TODO: Implement httpx-based local API call.
        """
        raise NotImplementedError("_call_local not yet implemented")

    def _call_anthropic(
        self,
        config: ModelConfig,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Call the Anthropic API for Claude models.

        Uses httpx to call the Anthropic Messages API.
        API key from environment variable specified in config.

        TODO: Implement Anthropic API call via httpx.
        """
        raise NotImplementedError("_call_anthropic not yet implemented")

    def _call_openai(
        self,
        config: ModelConfig,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Call the OpenAI API for GPT models.

        Uses httpx to call the OpenAI Chat Completions API.
        API key from environment variable specified in config.

        TODO: Implement OpenAI API call via httpx.
        """
        raise NotImplementedError("_call_openai not yet implemented")

    def _call_xai(
        self,
        config: ModelConfig,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Call the xAI API for Grok models.

        Grok is Intelligence role — web/community research, not code review.

        TODO: Implement xAI API call via httpx.
        """
        raise NotImplementedError("_call_xai not yet implemented")

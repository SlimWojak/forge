"""Tests for LocalModelAdapter protocol bridge."""
import pytest
from unittest.mock import MagicMock
from forge.models.adapter import LocalModelAdapter


class TestLocalModelAdapter:
    def test_satisfies_chat_completion_interface(self):
        """Adapter.chat_completion should return OpenAI-format dict."""
        mock_provider = MagicMock()
        mock_provider.raw_chat_completion.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Done"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        }

        adapter = LocalModelAdapter(provider=mock_provider, role="worker")
        result = adapter.chat_completion(
            messages=[{"role": "user", "content": "test"}],
            tools=None,
        )

        assert "choices" in result
        assert result["choices"][0]["message"]["content"] == "Done"
        mock_provider.raw_chat_completion.assert_called_once_with(
            role="worker",
            messages=[{"role": "user", "content": "test"}],
            tools=None,
        )

    def test_passes_tools_through(self):
        """Adapter should forward tools to provider."""
        mock_provider = MagicMock()
        mock_provider.raw_chat_completion.return_value = {
            "choices": [{"message": {"role": "assistant", "content": None, "tool_calls": []}}],
            "usage": {},
        }

        tools = [{"type": "function", "function": {"name": "test"}}]
        adapter = LocalModelAdapter(provider=mock_provider, role="worker")
        adapter.chat_completion(messages=[], tools=tools)

        mock_provider.raw_chat_completion.assert_called_once_with(
            role="worker", messages=[], tools=tools,
        )

    def test_different_roles(self):
        """Adapter should pass the configured role to provider."""
        mock_provider = MagicMock()
        mock_provider.raw_chat_completion.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {},
        }

        reviewer = LocalModelAdapter(provider=mock_provider, role="reviewer")
        reviewer.chat_completion(messages=[{"role": "user", "content": "review"}])

        mock_provider.raw_chat_completion.assert_called_once_with(
            role="reviewer",
            messages=[{"role": "user", "content": "review"}],
            tools=None,
        )

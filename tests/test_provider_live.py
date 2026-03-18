"""Tests for ModelProvider local endpoint integration."""
import pytest
from unittest.mock import patch, MagicMock
from forge.models.provider import ModelProvider, ModelConfig, CompletionRequest, CompletionResponse


class TestCallLocal:
    def test_call_local_returns_completion_response(self):
        """_call_local should POST to endpoint and return CompletionResponse."""
        provider = ModelProvider()
        config = ModelConfig(
            model="Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
            endpoint="http://localhost:8000/v1",
        )
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"role": "assistant", "content": "Hi there!"},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 3,
                "total_tokens": 8,
            },
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.post", return_value=mock_response) as mock_post:
            result = provider._call_local(config, request)

        assert isinstance(result, CompletionResponse)
        assert result.content == "Hi there!"
        assert result.tokens_in == 5
        assert result.tokens_out == 3
        mock_post.assert_called_once()

    def test_call_local_with_tools(self):
        """_call_local should pass tools in request body."""
        provider = ModelProvider()
        config = ModelConfig(
            model="Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
            endpoint="http://localhost:8000/v1",
        )
        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Use tool"}],
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{"id": "call_1", "function": {"name": "test_tool", "arguments": "{}"}}],
                },
                "finish_reason": "tool_calls",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.post", return_value=mock_response) as mock_post:
            result = provider._call_local(config, request, tools=tools)

        call_body = mock_post.call_args[1]["json"]
        assert "tools" in call_body

    def test_call_local_handles_thinking_tokens(self):
        """_call_local should extract content even when model uses thinking tokens."""
        provider = ModelProvider()
        config = ModelConfig(
            model="Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
            endpoint="http://localhost:8000/v1",
        )
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "The answer is 42.",
                    "reasoning": "Let me think about this...",
                },
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 5, "completion_tokens": 20, "total_tokens": 25},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.post", return_value=mock_response):
            result = provider._call_local(config, request)

        assert result.content == "The answer is 42."

    def test_call_local_api_error_raises(self):
        """_call_local should raise on HTTP errors."""
        provider = ModelProvider()
        config = ModelConfig(
            model="Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
            endpoint="http://localhost:8000/v1",
        )
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
        )

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server Error")

        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(Exception, match="Server Error"):
                provider._call_local(config, request)


class TestRawChatCompletion:
    def test_raw_returns_dict(self):
        """raw_chat_completion should return the raw API response dict."""
        provider = ModelProvider(config={
            "models": {
                "local": {
                    "worker": {
                        "endpoint": "http://localhost:8000/v1",
                        "model": "test-model",
                        "max_tokens": 100,
                        "temperature": 0.1,
                    },
                },
            },
        })

        expected = {
            "choices": [{"message": {"role": "assistant", "content": "hi"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.post", return_value=mock_response):
            result = provider.raw_chat_completion(
                role="worker",
                messages=[{"role": "user", "content": "test"}],
            )

        assert result == expected

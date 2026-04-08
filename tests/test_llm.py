"""Unit tests for LLM client and service."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.clients.ollama_client import OllamaClient
from app.core.errors import (
    LLMEmptyResponseError,
    LLMInternalError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.services.llm_service import LLMService


class TestOllamaClient:
    """Tests for OllamaClient class."""

    @pytest.mark.asyncio
    async def test_generate_response_success(self) -> None:
        """Test successful response generation."""
        client = OllamaClient(base_url="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(return_value=None)
        mock_response.json = MagicMock(return_value={"response": "Test answer"})

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(client, "_get_client", return_value=mock_client):
            result = await client.generate_response(prompt="Hello", model="test-model")

            assert result == "Test answer"
            mock_client.post.assert_called_once_with(
                "http://localhost:11434/api/generate",
                json={"model": "test-model", "prompt": "Hello", "stream": False},
            )

    @pytest.mark.asyncio
    async def test_generate_response_timeout(self) -> None:
        """Test timeout exception handling."""
        import httpx

        client = OllamaClient(base_url="http://localhost:11434")

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client.is_closed = False

        with patch.object(client, "_get_client", return_value=mock_client):
            with pytest.raises(LLMTimeoutError, match="Request timeout"):
                await client.generate_response(prompt="Hello", model="test-model")

    @pytest.mark.asyncio
    async def test_generate_response_unavailable(self) -> None:
        """Test service unavailable exception handling."""
        import httpx

        client = OllamaClient(base_url="http://localhost:11434")

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
        mock_client.is_closed = False

        with patch.object(client, "_get_client", return_value=mock_client):
            with pytest.raises(LLMUnavailableError, match="LLM is unavailable"):
                await client.generate_response(prompt="Hello", model="test-model")

    @pytest.mark.asyncio
    async def test_generate_response_empty(self) -> None:
        """Test empty response exception handling."""
        client = OllamaClient(base_url="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(return_value=None)
        mock_response.json = MagicMock(return_value={"response": ""})

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(client, "_get_client", return_value=mock_client):
            with pytest.raises(LLMEmptyResponseError, match="Empty response"):
                await client.generate_response(prompt="Hello", model="test-model")

    @pytest.mark.asyncio
    async def test_generate_response_internal_error(self) -> None:
        """Test internal error exception handling."""
        import httpx

        client = OllamaClient(base_url="http://localhost:11434")

        mock_request = MagicMock()
        mock_response_obj = MagicMock()
        mock_response_obj.status_code = 500

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Error", request=mock_request, response=mock_response_obj
            )
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(client, "_get_client", return_value=mock_client):
            with pytest.raises(LLMInternalError, match="Internal error"):
                await client.generate_response(prompt="Hello", model="test-model")


class TestLLMService:
    """Tests for LLMService class."""

    @pytest.mark.asyncio
    async def test_process_message_success(self) -> None:
        """Test successful message processing."""
        mock_client = AsyncMock()
        mock_client.generate_response = AsyncMock(return_value="LLM answer")

        service = LLMService(client=mock_client)
        result = await service.process_message(text="Hello", model="test-model")

        assert result == "LLM answer"
        mock_client.generate_response.assert_called_once_with(
            prompt="Hello", model="test-model"
        )

    @pytest.mark.asyncio
    async def test_process_message_timeout(self) -> None:
        """Test timeout fallback response."""
        mock_client = AsyncMock()
        mock_client.generate_response = AsyncMock(side_effect=LLMTimeoutError("Timeout"))

        service = LLMService(client=mock_client)
        result = await service.process_message(text="Hello", model="test-model")

        assert result == "Request timeout"

    @pytest.mark.asyncio
    async def test_process_message_unavailable(self) -> None:
        """Test unavailable fallback response."""
        mock_client = AsyncMock()
        mock_client.generate_response = AsyncMock(
            side_effect=LLMUnavailableError("Unavailable")
        )

        service = LLMService(client=mock_client)
        result = await service.process_message(text="Hello", model="test-model")

        assert result == "LLM is unavailable"

    @pytest.mark.asyncio
    async def test_process_message_empty(self) -> None:
        """Test empty response fallback."""
        mock_client = AsyncMock()
        mock_client.generate_response = AsyncMock(
            side_effect=LLMEmptyResponseError("Empty")
        )

        service = LLMService(client=mock_client)
        result = await service.process_message(text="Hello", model="test-model")

        assert result == "Empty response"

    @pytest.mark.asyncio
    async def test_process_message_internal_error(self) -> None:
        """Test internal error fallback."""
        mock_client = AsyncMock()
        mock_client.generate_response = AsyncMock(
            side_effect=LLMInternalError("Error")
        )

        service = LLMService(client=mock_client)
        result = await service.process_message(text="Hello", model="test-model")

        assert result == "Internal error"

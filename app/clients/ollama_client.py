"""Async HTTP client for Ollama API."""

from __future__ import annotations

import httpx

from app.core.errors import (
    LLMEmptyResponseError,
    LLMInternalError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.core.logger import logger


class OllamaClient:
    """Async client for interacting with Ollama LLM API."""

    # Timeout по умолчанию: connect=10s, read=120s (для медленных LLM), write=30s, pool=10s
    DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)

    def __init__(
        self,
        base_url: str,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        """Initialize Ollama client.

        Args:
            base_url: Base URL of Ollama API.
            timeout: Request timeout configuration. Uses DEFAULT_TIMEOUT if not provided.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client.

        Returns:
            Async HTTPX client instance.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def generate_response(
        self,
        prompt: str,
        model: str,
    ) -> str:
        """Generate response from LLM for given prompt.

        Args:
            prompt: Input text to process.
            model: Model name to use.

        Returns:
            Generated response text.

        Raises:
            LLMTimeoutError: If request times out.
            LLMUnavailableError: If service is unavailable.
            LLMEmptyResponseError: If response is empty.
            LLMInternalError: If internal error occurs.
        """
        client = await self._get_client()
        url = f"{self.base_url}/api/generate"

        # Ограничиваем количество токенов для предотвращения длинных ответов
        # и ускорения генерации
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 512,  # максимум 512 токенов в ответе
            },
        }

        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as e:
            logger.error("LLM request timed out", exc_info=True)
            raise LLMTimeoutError("Request timeout") from e
        except httpx.ConnectError as e:
            logger.error("LLM service unavailable", exc_info=True)
            raise LLMUnavailableError("LLM is unavailable") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM HTTP error: {e.response.status_code}", exc_info=True)
            raise LLMInternalError("Internal error") from e
        except Exception as e:
            logger.error("LLM request failed", exc_info=True)
            raise LLMInternalError("Internal error") from e

        response_text = data.get("response", "").strip()

        if not response_text:
            logger.warning("LLM returned empty response")
            raise LLMEmptyResponseError("Empty response")

        return response_text

    async def close(self) -> None:
        """Close HTTP client connection."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

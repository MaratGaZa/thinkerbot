"""LLM service for processing text through language model."""

from __future__ import annotations

from app.clients.ollama_client import OllamaClient
from app.core.errors import (
    LLMEmptyResponseError,
    LLMInternalError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.core.logger import logger


class LLMService:
    """Service layer for LLM interactions with error handling."""

    def __init__(self, client: OllamaClient) -> None:
        """Initialize LLM service.

        Args:
            client: Ollama client instance.
        """
        self.client = client

    async def process_message(self, text: str, model: str) -> str:
        """Process incoming message and return LLM response.

        Args:
            text: Input message text.
            model: Model name to use.

        Returns:
            LLM response text or fallback message on error.
        """
        try:
            logger.info(f"Processing message with model: {model}")
            return await self.client.generate_response(prompt=text, model=model)
        except LLMTimeoutError:
            logger.warning("LLM timeout occurred")
            return "Request timeout"
        except LLMUnavailableError:
            logger.warning("LLM service unavailable")
            return "LLM is unavailable"
        except LLMEmptyResponseError:
            logger.warning("LLM returned empty response")
            return "Empty response"
        except LLMInternalError:
            logger.warning("LLM internal error occurred")
            return "Internal error"
        except Exception as e:
            logger.error(f"Unexpected error in LLM service: {e}", exc_info=True)
            return "Internal error"

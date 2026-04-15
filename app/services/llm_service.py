"""LLM service for processing text through language model."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from app.clients.ollama_client import OllamaClient
from app.core.errors import (
    LLMEmptyResponseError,
    LLMInternalError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.core.logger import logger
from app.core.system_prompt import SystemPromptProvider


class LLMService:
    """Service layer for LLM interactions with error handling."""

    def __init__(
        self,
        client: OllamaClient,
        log_dir: str | None = None,
    ) -> None:
        """Initialize LLM service.

        Args:
            client: Ollama client instance.
            log_dir: Directory for context logs. Defaults to ./logs.
        """
        self.client = client
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).parent.parent.parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "context.log"

    async def process_message(self, text: str, model: str) -> str:
        """Process incoming message and return LLM response (backward compatible).

        Args:
            text: Input message text.
            model: Model name to use.

        Returns:
            LLM response text or fallback message on error.
        """
        # Build context with system prompt for backward compatibility
        system_prompt = SystemPromptProvider.get_prompt()
        context = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]
        return await self.process_context(context=context, model=model)

    async def process_context(self, context: list[dict], model: str) -> str:
        """Process conversation context and return LLM response.

        Args:
            context: List of message dicts with role and content.
            model: Model name to use.

        Returns:
            LLM response text or fallback message on error.
        """
        try:
            # Log context before sending to LLM
            self._log_context(context)

            # Convert context to prompt string for Ollama
            prompt = self._context_to_prompt(context)

            logger.info(f"Processing context with {len(context)} messages, model: {model}")
            return await self.client.generate_response(prompt=prompt, model=model)
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

    def _context_to_prompt(self, context: list[dict]) -> str:
        """Convert context list to prompt string for Ollama.

        System prompt is always first and formatted as an instruction.
        Other messages are formatted as conversation turns.

        Args:
            context: List of message dicts with role and content.

        Returns:
            Formatted prompt string.
        """
        lines = []

        for msg in context:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                # System prompt is formatted as an instruction block
                lines.append(f"<<<SYSTEM>>> {content} <<<END_SYSTEM>>>")
            elif role == "user":
                lines.append(f"User: {content}")
            elif role == "assistant":
                lines.append(f"Assistant: {content}")
            else:
                lines.append(f"{role}: {content}")

        return "\n\n".join(lines)

    def _count_tokens(self, context: list[dict]) -> int:
        """Estimate token count for context.

        Rough estimate: 1 token ≈ 1 word (split by whitespace).

        Args:
            context: List of message dicts with role and content.

        Returns:
            Estimated token count.
        """
        total = 0
        for msg in context:
            content = msg.get("content", "")
            total += len(content.split())
        return total

    def _log_context(self, context: list[dict], user_id: int | None = None) -> None:
        """Log context to file for auditability.

        Logs:
            - Full context (JSON format)
            - Context length (number of messages)
            - Token count estimate

        Args:
            context: List of message dicts with role and content.
            user_id: Optional Telegram user ID for logging.
        """
        timestamp = datetime.now().isoformat()
        token_count = self._count_tokens(context)

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] user_id={user_id or 'N/A'} ")
                f.write(f"messages={len(context)} tokens={token_count}\n")
                f.write(json.dumps(context, indent=2, ensure_ascii=False))
                f.write("\n" + "=" * 80 + "\n")
            logger.info(f"Context logged: {len(context)} messages, ~{token_count} tokens")
        except Exception as e:
            logger.error(f"Failed to log context: {e}", exc_info=True)

    async def summarize_text(self, text: str, model: str) -> str:
        """Summarize given text using the LLM.

        Args:
            text: Text to summarize.
            model: Model name to use.

        Returns:
            Summary text or empty string on error.
        """
        system_prompt = SystemPromptProvider.get_prompt()
        context = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Summarize the following conversation into a concise paragraph:\n\n{text}"},
        ]
        return await self.process_context(context, model)

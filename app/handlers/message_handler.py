"""Telegram message handler for text messages."""

from __future__ import annotations

from aiogram import types
from aiogram.types import Message

from app.core.logger import logger
from app.services.llm_service import LLMService


def split_text(text: str, max_length: int = 4000) -> list[str]:
    """Split text into chunks for Telegram message limit.

    Telegram allows maximum 4096 characters per message.
    This function splits text into chunks of max_length.

    Args:
        text: Text to split.
        max_length: Maximum length per chunk (default 4000).

    Returns:
        List of text chunks.
    """
    return [text[i : i + max_length] for i in range(0, len(text), max_length)]


class MessageHandler:
    """Handler for incoming Telegram messages."""

    def __init__(self, llm_service: LLMService) -> None:
        """Initialize message handler.

        Args:
            llm_service: LLM service instance.
        """
        self.llm_service = llm_service

    async def handle_text_message(
        self,
        message: Message,
        model: str,
    ) -> None:
        """Handle incoming text message.

        Args:
            message: Telegram message object.
            model: Model name to use.
        """
        if not message.text:
            logger.warning("Received message without text")
            return

        user_id = message.from_user.id
        logger.info(f"Received message from user {user_id}")

        response = await self.llm_service.process_message(
            text=message.text,
            model=model,
        )

        # Разбиваем ответ на части если он слишком длинный
        parts = split_text(response)
        for part in parts:
            await message.answer(part)

        logger.info(f"Sent response to user {user_id} ({len(parts)} message(s))")

    async def handle_other_content(self, message: Message) -> None:
        """Handle non-text messages by ignoring them.

        According to FR-1, bot should ignore photos, videos, files, stickers.

        Args:
            message: Telegram message object.
        """
        user_id = message.from_user.id
        content_type = message.content_type
        logger.debug(f"Ignoring {content_type} from user {user_id}")

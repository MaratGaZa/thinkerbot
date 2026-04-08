"""Telegram message handler for text messages."""

from __future__ import annotations

from aiogram import types
from aiogram.types import Message

from app.core.logger import logger
from app.services.llm_service import LLMService


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

        await message.answer(response)
        logger.info(f"Sent response to user {user_id}")

    async def handle_other_content(self, message: Message) -> None:
        """Handle non-text messages by ignoring them.

        According to FR-1, bot should ignore photos, videos, files, stickers.

        Args:
            message: Telegram message object.
        """
        user_id = message.from_user.id
        content_type = message.content_type
        logger.debug(f"Ignoring {content_type} from user {user_id}")

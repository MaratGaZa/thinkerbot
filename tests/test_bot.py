"""Unit tests for Telegram bot handlers."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from aiogram.types import Message, User

from app.handlers.message_handler import MessageHandler
from app.services.llm_service import LLMService


def create_mock_message(text: str | None = None, user_id: int = 123) -> Message:
    """Create a mock Telegram message.

    Args:
        text: Message text content.
        user_id: ID of the message sender.

    Returns:
        Mocked Message object.
    """
    user = User(id=user_id, is_bot=False, first_name="Test")

    message = MagicMock(spec=Message)
    message.from_user = user
    message.text = text
    message.content_type = "text" if text else "photo"
    message.answer = AsyncMock()

    return message


class TestMessageHandler:
    """Tests for MessageHandler class."""

    @pytest.mark.asyncio
    async def test_handle_text_message(self) -> None:
        """Test handling of text message."""
        mock_llm_service = AsyncMock(spec=LLMService)
        mock_llm_service.process_message = AsyncMock(return_value="Bot response")

        handler = MessageHandler(llm_service=mock_llm_service)
        message = create_mock_message(text="Hello bot")

        await handler.handle_text_message(message=message, model="test-model")

        mock_llm_service.process_message.assert_called_once_with(
            text="Hello bot", model="test-model"
        )
        message.answer.assert_called_once_with("Bot response")

    @pytest.mark.asyncio
    async def test_handle_text_message_no_text(self) -> None:
        """Test handling of message without text."""
        mock_llm_service = AsyncMock(spec=LLMService)

        handler = MessageHandler(llm_service=mock_llm_service)
        message = create_mock_message(text=None)

        await handler.handle_text_message(message=message, model="test-model")

        mock_llm_service.process_message.assert_not_called()
        message.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_other_content_photo(self) -> None:
        """Test ignoring photo messages."""
        mock_llm_service = AsyncMock(spec=LLMService)

        handler = MessageHandler(llm_service=mock_llm_service)
        message = create_mock_message(text=None)
        message.content_type = "photo"

        await handler.handle_other_content(message)

        mock_llm_service.process_message.assert_not_called()
        message.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_other_content_video(self) -> None:
        """Test ignoring video messages."""
        mock_llm_service = AsyncMock(spec=LLMService)

        handler = MessageHandler(llm_service=mock_llm_service)
        message = create_mock_message(text=None)
        message.content_type = "video"

        await handler.handle_other_content(message)

        mock_llm_service.process_message.assert_not_called()
        message.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_other_content_sticker(self) -> None:
        """Test ignoring sticker messages."""
        mock_llm_service = AsyncMock(spec=LLMService)

        handler = MessageHandler(llm_service=mock_llm_service)
        message = create_mock_message(text=None)
        message.content_type = "sticker"

        await handler.handle_other_content(message)

        mock_llm_service.process_message.assert_not_called()
        message.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_other_content_document(self) -> None:
        """Test ignoring document messages."""
        mock_llm_service = AsyncMock(spec=LLMService)

        handler = MessageHandler(llm_service=mock_llm_service)
        message = create_mock_message(text=None)
        message.content_type = "document"

        await handler.handle_other_content(message)

        mock_llm_service.process_message.assert_not_called()
        message.answer.assert_not_called()

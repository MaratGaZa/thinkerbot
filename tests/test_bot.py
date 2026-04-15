"""Unit tests for Telegram bot handlers."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from aiogram.types import Message, User

from app.history.history_manager import HistoryManager
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
    thinking_message = AsyncMock()
    thinking_message.delete = AsyncMock()
    message.answer.return_value = thinking_message

    return message


class TestMessageHandler:
    """Tests for MessageHandler class."""

    @pytest.mark.asyncio
    async def test_handle_text_message(self) -> None:
        """Test handling of text message."""
        mock_llm_service = AsyncMock(spec=LLMService)
        mock_llm_service.process_context = AsyncMock(return_value="Bot response")
        mock_llm_service.summarize_text = AsyncMock(return_value="Summary")

        history_manager = HistoryManager(max_messages=20, max_tokens=2000, summarize_trigger=5)
        handler = MessageHandler(
            llm_service=mock_llm_service,
            history_manager=history_manager,
            enable_history=True,
        )
        message = create_mock_message(text="Hello bot")

        await handler.handle_text_message(message=message, model="test-model")
        mock_llm_service.process_context.assert_called_once()
        context = mock_llm_service.process_context.call_args.kwargs["context"]
        assert context[0]["role"] == "system"
        assert context[-1]["role"] == "user"
        assert context[-1]["content"] == "Hello bot"
        assert mock_llm_service.process_context.call_args.kwargs["user_id"] == 123
        message.answer.assert_any_call("⏳ Thinking...")
        message.answer.assert_any_call("Bot response")

    @pytest.mark.asyncio
    async def test_handle_text_message_no_text(self) -> None:
        """Test handling of message without text."""
        mock_llm_service = AsyncMock(spec=LLMService)

        handler = MessageHandler(llm_service=mock_llm_service)
        message = create_mock_message(text=None)

        await handler.handle_text_message(message=message, model="test-model")

        mock_llm_service.process_message.assert_not_called()
        mock_llm_service.process_context.assert_not_called()
        message.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_history_is_isolated_by_user(self) -> None:
        """Test that history is stored independently per user."""
        mock_llm_service = AsyncMock(spec=LLMService)
        mock_llm_service.process_context = AsyncMock(return_value="answer")
        mock_llm_service.summarize_text = AsyncMock(return_value="Summary")

        history_manager = HistoryManager(max_messages=20, max_tokens=2000, summarize_trigger=5)
        handler = MessageHandler(
            llm_service=mock_llm_service,
            history_manager=history_manager,
            enable_history=True,
        )
        message_1 = create_mock_message(text="first", user_id=1)
        message_2 = create_mock_message(text="second", user_id=2)

        await handler.handle_text_message(message=message_1, model="test-model")
        await handler.handle_text_message(message=message_2, model="test-model")

        user_1_history = history_manager.get(1)
        user_2_history = history_manager.get(2)
        assert any(msg.content == "first" for msg in user_1_history)
        assert all(msg.content != "second" for msg in user_1_history)
        assert any(msg.content == "second" for msg in user_2_history)

    @pytest.mark.asyncio
    async def test_handle_other_content_photo(self) -> None:
        """Test ignoring photo messages."""
        mock_llm_service = AsyncMock(spec=LLMService)

        handler = MessageHandler(llm_service=mock_llm_service)
        message = create_mock_message(text=None)
        message.content_type = "photo"

        await handler.handle_other_content(message)

        mock_llm_service.process_message.assert_not_called()
        mock_llm_service.process_context.assert_not_called()
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
        mock_llm_service.process_context.assert_not_called()
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
        mock_llm_service.process_context.assert_not_called()
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
        mock_llm_service.process_context.assert_not_called()
        message.answer.assert_not_called()

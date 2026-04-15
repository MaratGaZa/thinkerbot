"""Telegram message handler for text messages."""

from __future__ import annotations

from aiogram import types
from aiogram.types import Message

from app.core.logger import logger
from app.services.llm_service import LLMService
from app.history.history_manager import HistoryManager, Message as HistoryMessage
from app.core.system_prompt import SystemPromptProvider


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

    def __init__(
        self,
        llm_service: LLMService,
        history_manager: HistoryManager | None = None,
        enable_history: bool = True,
    ) -> None:
        """Initialize message handler.

        Args:
            llm_service: LLM service instance.
            history_manager: Optional history manager instance.
            enable_history: Whether to use history tracking.
        """
        self.llm_service = llm_service
        self.history_manager = history_manager
        self.enable_history = enable_history

        # Set up summarization callback if history is enabled
        if self.history_manager and self.enable_history:
            self.history_manager.set_summarization_callback(
                self._summarize_callback
            )

    async def _summarize_callback(self, user_id: int, history_text: str) -> str:
        """Callback for history summarization.

        Args:
            user_id: Telegram user ID.
            history_text: Text to summarize.

        Returns:
            Summary text.
        """
        # Use a lightweight model for summarization
        summary = await self.llm_service.summarize_text(history_text, model="qwen3.5:0.8b")
        return summary if summary else "Previous conversation summary."

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

        # Отправляем уведомление о начале обработки
        thinking_msg = await message.answer("⏳ Thinking...")

        if self.enable_history and self.history_manager:
            response = await self._handle_with_history(message, model)
        else:
            response = await self.llm_service.process_message(
                text=message.text,
                model=model,
            )

        # Удаляем сообщение "Thinking..."
        await thinking_msg.delete()

        # Разбиваем ответ на части если он слишком длинный
        parts = split_text(response)
        for part in parts:
            await message.answer(part)

        logger.info(f"Sent response to user {user_id} ({len(parts)} message(s))")

    async def _handle_with_history(self, message: Message, model: str) -> str:
        """Handle message with history tracking.

        Args:
            message: Telegram message object.
            model: Model name to use.

        Returns:
            LLM response text.
        """
        user_id = message.from_user.id

        # Get existing history
        history = self.history_manager.get(user_id)

        # Build context: system prompt + history + current message
        system_prompt = SystemPromptProvider.get_prompt()
        context = [{"role": "system", "content": system_prompt}]
        context.extend([msg.to_dict() for msg in history])
        context.append({"role": "user", "content": message.text})

        # Add user message to history
        user_msg = HistoryMessage(role="user", content=message.text)
        self.history_manager.add(user_id, user_msg)

        # Enforce limits (may trigger summarization)
        await self.history_manager.enforce_limits(user_id)

        # Process context and get response
        response = await self.llm_service.process_context(context=context, model=model)

        # Add assistant response to history
        if response:
            assistant_msg = HistoryMessage(role="assistant", content=response)
            self.history_manager.add(user_id, assistant_msg)

        return response

    async def handle_other_content(self, message: Message) -> None:
        """Handle non-text messages by ignoring them.

        According to FR-1, bot should ignore photos, videos, files, stickers.

        Args:
            message: Telegram message object.
        """
        user_id = message.from_user.id
        content_type = message.content_type
        logger.debug(f"Ignoring {content_type} from user {user_id}")

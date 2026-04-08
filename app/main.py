"""Main entry point for ThinkerBot Telegram bot."""

from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

from app.clients.ollama_client import OllamaClient
from app.core.config import config
from app.core.logger import logger
from app.handlers.message_handler import MessageHandler
from app.services.llm_service import LLMService


class BotState:
    """Bot state storing current model selection."""

    current_model: str = config.model_name


def create_bot() -> Bot:
    """Create and return configured Bot instance.

    Returns:
        Configured aiogram Bot instance.
    """
    return Bot(token=config.telegram_token)


def create_dispatcher() -> Dispatcher:
    """Create and return configured Dispatcher instance.

    Returns:
        Configured aiogram Dispatcher instance.
    """
    return Dispatcher()


def register_handlers(
    dp: Dispatcher,
    bot: Bot,
    message_handler: MessageHandler,
) -> None:
    """Register all message handlers.

    Args:
        dp: Dispatcher instance.
        bot: Bot instance (unused, kept for signature compatibility).
        message_handler: MessageHandler instance.
    """

    @dp.message(lambda msg: msg.text == "/model")
    async def model_command(message: Message) -> None:
        """Handle /model command - show model selection keyboard."""
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=model,
                        callback_data=f"set_model_{model}",
                    )
                ]
                for model in config.AVAILABLE_MODELS
            ]
        )
        await message.answer(
            f"Current model: {BotState.current_model}\nSelect a model:",
            reply_markup=keyboard,
        )

    @dp.callback_query(lambda c: c.data.startswith("set_model_"))
    async def set_model_callback(callback: CallbackQuery) -> None:
        """Handle model selection callback."""
        model = callback.data.replace("set_model_", "")
        if model in config.AVAILABLE_MODELS:
            BotState.current_model = model
            await callback.answer(f"Model changed to {model}")
            await callback.message.edit_text(f"Model changed to: {model}")
        else:
            await callback.answer("Invalid model")

    @dp.message(lambda msg: msg.text is not None)
    async def text_handler(message: Message) -> None:
        await message_handler.handle_text_message(
            message=message,
            model=BotState.current_model,
        )

    @dp.message()
    async def other_handler(message: Message) -> None:
        await message_handler.handle_other_content(message)


async def run_polling() -> None:
    """Run bot with polling mode.

    This function initializes all components and starts
    the polling loop for receiving Telegram updates.
    """
    config.validate()

    logger.info("Starting ThinkerBot...")

    ollama_client = OllamaClient(
        base_url=config.ollama_url,
        timeout=config.timeout,
    )
    llm_service = LLMService(client=ollama_client)
    message_handler = MessageHandler(llm_service=llm_service)

    bot = create_bot()
    dp = create_dispatcher()

    register_handlers(dp, bot, message_handler)

    logger.info(f"Using model: {BotState.current_model}")
    logger.info(f"Available models: {config.AVAILABLE_MODELS}")
    logger.info("Bot started with polling mode")

    try:
        await dp.start_polling(bot)
    finally:
        await ollama_client.close()
        await bot.session.close()
        logger.info("Bot stopped")


async def main() -> None:
    """Main entry point with error handling."""
    try:
        await run_polling()
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

"""Main entry point for ThinkerBot Telegram bot."""

from __future__ import annotations

import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
    FSInputFile,
)

from app.clients.ollama_client import OllamaClient
from app.core.config import config
from app.core.logger import logger
from app.core.system_prompt import SystemPromptProvider
from app.handlers.message_handler import MessageHandler
from app.services.llm_service import LLMService
from app.history.history_manager import HistoryManager


class BotState:
    """Bot state storing current model selection."""

    current_model: str = config.model_name


# Mapping моделей для отображения в Telegram
MODEL_DISPLAY_NAMES = {
    "qwen2.5:3b": "турба",
    "qwen3.5:0.8b": "турба версия 2",
    "qwen3.5:2b": "оптимальная",
    "qwen3.5:4b": "точная",
    "gpt-oss:20b": "умная",
}

# Путь к директории с изображениями
IMG_DIR = Path(__file__).parent.parent / "img"


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


def get_model_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard with model selection buttons.

    Returns:
        Inline keyboard with display names for models.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=MODEL_DISPLAY_NAMES.get(model, model),
                    callback_data=f"set_model_{model}",
                )
            ]
            for model in config.AVAILABLE_MODELS
        ]
    )


def get_welcome_text() -> str:
    """Generate welcome message with bot info and commands.

    Returns:
        Welcome text string.
    """
    return (
        "🤖 **ThinkerBot** — Telegram-бот с локальной LLM\n\n"
        "📝 **Что делает:**\n"
        "Принимает текстовые сообщения и отправляет их в локальную нейросеть (Ollama),\n"
        "возвращая умный ответ.\n\n"
        "⚙️ **Команды:**\n"
        "/start - Запустить бота и показать это сообщение\n"
        "/help - Информация о боте\n"
        "/model - Выбрать модель для обработки\n"
        "/sys - Изменить системный промпт (поведение бота)\n"
        "/sysreset - Сбросить системный промпт к умолчанию\n\n"
        "🧠 **Доступные модели:**\n"
        "• турба — быстрая, для простых задач\n"
        "• турба версия 2 — самая лёгкая и быстрая\n"
        "• оптимальная — баланс скорости и качества\n"
        "• точная — более точные ответы\n"
        "• умная — самая умная, но медленная"
    )


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

    @dp.message(lambda msg: msg.text == "/start")
    async def start_command(message: Message) -> None:
        """Handle /start command - show welcome message with wallpaper."""
        wallpaper_path = IMG_DIR / "wallpaper.jpg"

        if wallpaper_path.exists():
            photo = FSInputFile(str(wallpaper_path))
            await message.answer_photo(
                photo=photo,
                caption=get_welcome_text(),
                parse_mode="Markdown",
            )
        else:
            await message.answer(
                get_welcome_text(),
                parse_mode="Markdown",
            )

    @dp.message(lambda msg: msg.text == "/help")
    async def help_command(message: Message) -> None:
        """Handle /help command - show bot info."""
        await message.answer(
            get_welcome_text(),
            parse_mode="Markdown",
        )

    @dp.message(lambda msg: msg.text == "/model")
    async def model_command(message: Message) -> None:
        """Handle /model command - show model selection keyboard."""
        current_model_name = MODEL_DISPLAY_NAMES.get(
            BotState.current_model,
            BotState.current_model,
        )
        keyboard = get_model_keyboard()
        await message.answer(
            f"Текущая модель: {current_model_name}\n\nВыберите модель:",
            reply_markup=keyboard,
        )

    @dp.message(lambda msg: msg.text == "/sys" or (msg.text and msg.text.startswith("/sys ")))
    async def sys_command(message: Message) -> None:
        """Handle /sys command - change system prompt.

        Usage: /sys <new system prompt>
        """
        new_prompt = message.text[4:].strip()  # Remove "/sys" prefix
        if not new_prompt:
            await message.answer(
                "❌ Использование: `/sys <текст промпта>`\n\n"
                "Пример: `/sys Ты опытный программист, отвечаешь кратко по делу`",
                parse_mode="Markdown",
            )
            return

        SystemPromptProvider.set_prompt(new_prompt)
        logger.info(f"System prompt changed by user {message.from_user.id}: {new_prompt[:50]}...")
        await message.answer(
            "✅ Системный промпт изменён:\n\n"
            f"_{new_prompt}_",
            parse_mode="Markdown",
        )

    @dp.message(lambda msg: msg.text == "/sysreset")
    async def sysreset_command(message: Message) -> None:
        """Handle /sysreset command - reset system prompt to default."""
        SystemPromptProvider.reset_prompt()
        logger.info(f"System prompt reset to default by user {message.from_user.id}")
        await message.answer(
            "✅ Системный промпт сброшен к значению по умолчанию",
        )

    @dp.callback_query(lambda c: c.data.startswith("set_model_"))
    async def set_model_callback(callback: CallbackQuery) -> None:
        """Handle model selection callback."""
        model = callback.data.replace("set_model_", "")
        if model in config.AVAILABLE_MODELS:
            BotState.current_model = model
            display_name = MODEL_DISPLAY_NAMES.get(model, model)
            await callback.answer(f"Модель изменена на: {display_name}")
            await callback.message.edit_text(f"Модель изменена на: {display_name}")
        else:
            await callback.answer("Неверная модель")

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

    # Initialize history manager with config settings
    history_manager = HistoryManager(
        max_messages=config.history_max_messages,
        max_tokens=config.history_max_tokens,
        summarize_trigger=config.history_summarize_trigger,
    )

    message_handler = MessageHandler(
        llm_service=llm_service,
        history_manager=history_manager,
        enable_history=config.enable_history,
    )

    bot = create_bot()
    dp = create_dispatcher()

    register_handlers(dp, bot, message_handler)

    logger.info(f"Using model: {BotState.current_model}")
    logger.info(f"Available models: {config.AVAILABLE_MODELS}")
    logger.info(f"History enabled: {config.enable_history}")
    logger.info(f"History limits: max_messages={config.history_max_messages}, max_tokens={config.history_max_tokens}")
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

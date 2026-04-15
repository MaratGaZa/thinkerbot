"""System prompt provider for LLM context injection."""

from __future__ import annotations


class SystemPromptProvider:
    """Provides static system prompt for LLM requests.

    The system prompt is always the first element in the context
    and instructs the LLM on its role and behavior.
    """

    DEFAULT_SYSTEM_PROMPT = (
        "You are ThinkerBot, a helpful Telegram bot assistant "
        "powered by a local LLM. You provide concise, accurate, "
        "and context-aware responses to user messages. "
        "You maintain conversation context and refer to previous "
        "messages when relevant."
    )

    @classmethod
    def get_prompt(cls) -> str:
        """Get the system prompt string.

        Returns:
            System prompt text.
        """
        return cls.DEFAULT_SYSTEM_PROMPT

    @classmethod
    def set_prompt(cls, prompt: str) -> None:
        """Override the default system prompt.

        Args:
            prompt: New system prompt text.
        """
        cls.DEFAULT_SYSTEM_PROMPT = prompt

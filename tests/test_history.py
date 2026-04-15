"""Unit tests for history manager and system prompt behavior."""

from __future__ import annotations

import pytest

from app.core.system_prompt import SystemPromptProvider
from app.history.history_manager import HistoryManager, Message


class TestHistoryManager:
    """Tests for HistoryManager class."""

    @pytest.mark.asyncio
    async def test_enforce_limits_triggers_summarization_at_threshold(self) -> None:
        """Test summarization starts once message threshold is reached."""
        manager = HistoryManager(max_messages=20, max_tokens=2000, summarize_trigger=5)

        async def summarize(_: int, text: str) -> str:
            return f"summary::{text[:20]}"

        manager.set_summarization_callback(summarize)
        user_id = 1
        for i in range(6):
            manager.add(user_id, Message(role="user", content=f"msg {i}"))

        await manager.enforce_limits(user_id)

        history = manager.get(user_id)
        assert history[0].role == "assistant"
        assert history[0].content.startswith("summary::")
        assert len(history) <= 6


class TestSystemPromptProvider:
    """Tests for system prompt provider mutability/reset."""

    def test_set_and_reset_prompt(self) -> None:
        """Test prompt can be changed and reset to default."""
        original_prompt = SystemPromptProvider.DEFAULT_SYSTEM_PROMPT
        SystemPromptProvider.set_prompt("temporary prompt")
        assert SystemPromptProvider.get_prompt() == "temporary prompt"

        SystemPromptProvider.reset_prompt()
        assert SystemPromptProvider.get_prompt() == original_prompt

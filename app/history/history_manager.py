"""In-memory history manager for conversation context per user."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import time

from app.core.logger import logger


@dataclass
class Message:
    """Single conversation message with role and content."""

    role: str  # "user", "assistant", or "system"
    content: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Convert message to dictionary for serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Message:
        """Create Message from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", time.time()),
        )


class HistoryManager:
    """Manages conversation history per user with limit enforcement and summarization.

    Storage format: {user_id: List[Message]}
    History is stored in memory and lost on restart.
    """

    def __init__(
        self,
        max_messages: int = 20,
        max_tokens: int = 2000,
        summarize_trigger: int = 10,
    ) -> None:
        """Initialize history manager.

        Args:
            max_messages: Maximum messages to keep per user.
            max_tokens: Maximum token estimate per user.
            summarize_trigger: Number of messages before triggering summarization.
        """
        self._storage: Dict[int, List[Message]] = {}
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.summarize_trigger = summarize_trigger
        self._summarization_callback = None

    def set_summarization_callback(self, callback) -> None:
        """Set callback function for summarization.

        Args:
            callback: Async function that takes (user_id, history_text) and returns summary.
        """
        self._summarization_callback = callback

    def get(self, user_id: int) -> List[Message]:
        """Get conversation history for user.

        Args:
            user_id: Telegram user ID.

        Returns:
            List of messages in chronological order.
        """
        return self._storage.get(user_id, []).copy()

    def add(self, user_id: int, message: Message) -> None:
        """Add message to user's history.

        Args:
            user_id: Telegram user ID.
            message: Message to add.
        """
        if user_id not in self._storage:
            self._storage[user_id] = []

        self._storage[user_id].append(message)
        logger.debug(f"Added {message.role} message for user {user_id}")

    def clear(self, user_id: int) -> None:
        """Clear history for user.

        Args:
            user_id: Telegram user ID.
        """
        if user_id in self._storage:
            del self._storage[user_id]
            logger.debug(f"Cleared history for user {user_id}")

    def count_tokens(self, user_id: int) -> int:
        """Estimate token count for user's history.

        Rough estimate: 1 token ≈ 1 word (split by whitespace).

        Args:
            user_id: Telegram user ID.

        Returns:
            Estimated token count.
        """
        messages = self._storage.get(user_id, [])
        return sum(len(msg.content.split()) for msg in messages)

    def message_count(self, user_id: int) -> int:
        """Get number of messages in user's history.

        Args:
            user_id: Telegram user ID.

        Returns:
            Number of messages.
        """
        return len(self._storage.get(user_id, []))

    async def enforce_limits(self, user_id: int) -> None:
        """Enforce message and token limits, triggering summarization if needed.

        Args:
            user_id: Telegram user ID.
        """
        messages = self._storage.get(user_id, [])

        if not messages:
            return

        # Check if summarization is needed
        needs_summarization = (
            len(messages) >= self.max_messages or
            self.count_tokens(user_id) >= self.max_tokens
        )

        if needs_summarization and self._summarization_callback:
            logger.info(f"Triggering summarization for user {user_id}")
            await self._summarize(user_id)

        # Trim if still over limit after summarization
        self._trim_if_needed(user_id)

    async def _summarize(self, user_id: int) -> None:
        """Summarize old messages and replace with summary.

        Args:
            user_id: Telegram user ID.
        """
        messages = self._storage.get(user_id, [])

        if len(messages) < self.summarize_trigger:
            return

        # Keep the most recent messages (last 5)
        messages_to_summarize = messages[:-5]
        recent_messages = messages[-5:]

        if not messages_to_summarize:
            return

        # Build text for summarization
        history_text = "\n".join(
            f"{msg.role}: {msg.content}" for msg in messages_to_summarize
        )

        try:
            summary = await self._summarization_callback(user_id, history_text)

            # Replace old messages with summary
            summary_msg = Message(role="assistant", content=summary)
            self._storage[user_id] = [summary_msg] + recent_messages

            logger.info(f"Summarized {len(messages_to_summarize)} messages for user {user_id}")
        except Exception as e:
            logger.error(f"Summarization failed for user {user_id}: {e}", exc_info=True)
            # Fallback: just trim without summarization
            self._trim_if_needed(user_id)

    def _trim_if_needed(self, user_id: int) -> None:
        """Trim oldest messages if over max_messages limit.

        Args:
            user_id: Telegram user ID.
        """
        messages = self._storage.get(user_id, [])

        while len(messages) > self.max_messages:
            # Remove oldest non-system message
            for i, msg in enumerate(messages):
                if msg.role != "system":
                    messages.pop(i)
                    break
            else:
                # All messages are system, break to avoid infinite loop
                break

        self._storage[user_id] = messages

    def to_dict(self, user_id: int) -> dict:
        """Convert user's history to dictionary for logging.

        Args:
            user_id: Telegram user ID.

        Returns:
            Dictionary with user_id and messages list.
        """
        messages = self._storage.get(user_id, [])
        return {
            "user_id": user_id,
            "messages": [msg.to_dict() for msg in messages],
            "token_count": self.count_tokens(user_id),
            "message_count": len(messages),
        }

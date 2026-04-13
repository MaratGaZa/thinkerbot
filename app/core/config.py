"""Application configuration loaded from environment variables."""

import os

import httpx


class Config:
    """Configuration container for application settings."""

    AVAILABLE_MODELS: tuple[str, ...] = (
        "qwen2.5:3b",
        "qwen3.5:0.8b",
        "qwen3.5:2b",
        "qwen3.5:4b",
        "gpt-oss:20b",
    )

    def __init__(self) -> None:
        self.telegram_token: str = os.getenv("TEL_BOT_TOK", "")
        self.ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model_name: str = os.getenv("MODEL_NAME", "qwen2.5:3b")
        # Timeout для read (генерация ответа LLM) - 120 секунд
        self.timeout: httpx.Timeout = httpx.Timeout(
            connect=10.0,
            read=float(os.getenv("TIMEOUT_READ", "180")),
            write=30.0,
            pool=10.0,
        )

    def validate(self) -> None:
        """Validate required configuration values.

        Raises:
            ValueError: If required configuration is missing.
        """
        if not self.telegram_token:
            raise ValueError("TEL_BOT_TOK environment variable is required")


config = Config()

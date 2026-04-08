"""Application configuration loaded from environment variables."""

import os


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
        self.timeout: int = int(os.getenv("TIMEOUT", "30"))

    def validate(self) -> None:
        """Validate required configuration values.

        Raises:
            ValueError: If required configuration is missing.
        """
        if not self.telegram_token:
            raise ValueError("TEL_BOT_TOK environment variable is required")


config = Config()

"""Custom exception classes for the application."""


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class LLMUnavailableError(LLMError):
    """Raised when LLM service is unavailable."""

    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""

    pass


class LLMEmptyResponseError(LLMError):
    """Raised when LLM returns an empty response."""

    pass


class LLMInternalError(LLMError):
    """Raised when LLM returns an internal error."""

    pass

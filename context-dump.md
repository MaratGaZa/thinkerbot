# Context Dump — ThinkerBot Project Analysis

## 1. Overview

**Project Name:** ThinkerBot  
**Description:** Telegram bot with local LLM integration (Ollama)  
**Python Version:** 3.12+  
**Architecture Pattern:** Layered architecture with separation of concerns

---

## 2. Project Structure

```
thinkerbot/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Entry point, polling setup
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Environment-based configuration
│   │   ├── errors.py           # Custom exception hierarchy
│   │   ├── logger.py           # Structured logging setup
│   │   └── system_prompt.py    # Static system prompt provider
│   ├── clients/
│   │   ├── __init__.py
│   │   └── ollama_client.py    # Async HTTP client for Ollama API
│   ├── services/
│   │   ├── __init__.py
│   │   └── llm_service.py      # LLM service layer with error handling
│   ├── handlers/
│   │   ├── __init__.py
│   │   └── message_handler.py  # Telegram message handlers
│   ├── history/
│   │   └── history_manager.py  # In‑memory per‑user history storage
│   └── img/
│       └── wallpaper.jpg       # Welcome image
├── tests/
│   ├── __init__.py
│   ├── test_bot.py             # Handler tests
│   └── test_llm.py             # LLM client/service tests
├── pyproject.toml              # Project metadata & dependencies
├── requirements.txt            # Pip dependencies
├── .env.example                # Environment template
├── README.md                   # User documentation
├── PROJECT_PLAN.md             # Development plan
└── PROJECT_PROMPTS.md          # Development prompts history
```

---

## 3. Architecture Analysis

### 3.1 Request Flow

```
Telegram User → Telegram API → aiogram (polling) → main.py
                                                      ↓
                                              Dispatcher routes
                                                      ↓
                                              MessageHandler
                                                      ↓
                                              LLMService
                                                      ↓
                                              HistoryManager
                                                      ↓
                                              OllamaClient
                                                      ↓
                                              Ollama API (localhost:11434)
```

### 3.2 Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| `main.py` | Bot initialization, polling loop, handler registration |
| `handlers/message_handler.py` | Telegram message processing, UI interactions |
| `services/llm_service.py` | Business logic, error handling, fallback responses |
| `clients/ollama_client.py` | HTTP communication with Ollama API |
| `core/config.py` | Environment variable management |
| `core/logger.py` | Structured logging |
| `core/system_prompt.py` | Provides a static system prompt |
| `history/history_manager.py` | Stores per‑user history, enforces limits, triggers summarization |
| `core/errors.py` | Custom exception hierarchy |

### 3.3 History & State Management

**History Storage:** NEW  
- The bot now maintains an **in‑memory per‑user history** via `HistoryManager`.  
- Each history entry follows the format:  
  ```json
  { "role": "user"/"assistant", "content": "…"} 
  ```  
- History is capped at **`MAX_HISTORY_MESSAGES` (10 by default)**. When the limit is exceeded, the manager **summarizes** older messages using the LLM and replaces them with a single summary entry.  
- A **system prompt** is prepended to every context and never removed.

**Stateful Elements:**  
- `BotState.current_model` — class‑level variable storing the selected model (volatile)  
- `HistoryManager` — in‑memory storage per user

---

## 4. Libraries & Versions

### 4.1 Core Dependencies (from `pyproject.toml` / `requirements.txt`)

| Library | Version | Purpose |
|---------|---------|---------|
| `aiogram` | ≥3.0.0 | Async Telegram Bot API framework |
| `httpx` | ≥0.24.0 | Async HTTP client for Ollama API |
| `python-dotenv` | ≥1.0.0 | Environment variable loading |

### 4.2 Test Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| `pytest` | ≥7.0.0 | Testing framework |
| `pytest-asyncio` | ≥0.21.0 | Async test support |

### 4.3 External Dependencies (Required)

| Component | Version/Model | Purpose |
|-----------|---------------|---------|
| Ollama | Latest | Local LLM runtime |
| qwen2.5:3b | — | Default model (lightweight) |
| qwen3.5:0.8b | — | Lightest & fastest |
| qwen3.5:2b | — | Balanced |
| qwen3.5:4b | — | More accurate |
| gpt-oss:20b | — | Most capable (GPU‑intensive) |

---

## 5. Test Suite

*No changes to the existing test suite are required for the new stateful features, but additional tests for `HistoryManager` and context logging are recommended.*

---

## 6. Interfaces & Contracts

### 6.1 OllamaClient Interface

```python
class OllamaClient:
    def __init__(self, base_url: str, timeout: httpx.Timeout)
    async def generate_response(self, prompt: str, model: str) -> str
    async def close(self) -> None
```

**Contract:**  
- Raises `LLMTimeoutError` on timeout  
- Raises `LLMUnavailableError` on connection failure  
- Raises `LLMEmptyResponseError` on empty response  
- Raises `LLMInternalError` on HTTP errors

### 6.2 LLMService Interface

```python
class LLMService:
    def __init__(self, client: OllamaClient)
    async def process_message(self, text: str, model: str) -> str
```

**Contract:**  
- Never raises exceptions — always returns a fallback string on error  
- Fallback responses: "Request timeout", "LLM is unavailable", "Empty response", "Internal error"

### 6.3 MessageHandler Interface

```python
class MessageHandler:
    def __init__(self, llm_service: LLMService, history_manager: HistoryManager)
    async def handle_text_message(self, message: Message, model: str)
```

**Contract:**  
- Sends a *Thinking…* notification  
- Deletes the notification after receiving the LLM response  
- Splits responses into 4000‑char chunks  
- Uses `HistoryManager` to maintain conversation context

---

## 7. Technical Design (Stateful Enhancements)

1. **HistoryManager** – In‑memory per‑user storage with limit enforcement and summarization.  
2. **SystemPromptProvider** – Static prompt injected at context start.  
3. **Context Logging** – The full prompt sent to LLM is serialized (YAML) and appended to `logs/context.log`.  
4. **Summarization** – Triggered when `MAX_HISTORY_MESSAGES` is exceeded; LLM generates a concise summary, which replaces older entries.

---

## 8. Future Improvements

- Persist history to a lightweight database (Redis or SQLite) for crash recovery.  
- Implement token‑based limits instead of message count for more accurate LLM usage.  
- Add an async cache for summarization results to reduce repeated summarization costs.  
- Introduce a CLI utility to validate environment variables before bot startup.

---
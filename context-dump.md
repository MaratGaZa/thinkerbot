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
│   │   └── logger.py           # Structured logging setup
│   ├── clients/
│   │   ├── __init__.py
│   │   └── ollama_client.py    # Async HTTP client for Ollama API
│   ├── services/
│   │   ├── __init__.py
│   │   └── llm_service.py      # LLM service layer with error handling
│   ├── handlers/
│   │   ├── __init__.py
│   │   └── message_handler.py  # Telegram message handlers
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
| `core/errors.py` | Custom exception hierarchy |

### 3.3 History & State Management

**History Storage:** NONE

- The bot is **stateless** — no conversation history is stored
- Each message is processed independently
- No database or persistence layer exists
- `BotState` class in `main.py` only stores the current model selection (in-memory, lost on restart)

**Stateful Elements:**
- `BotState.current_model` — class-level variable storing selected model (volatile)

---

## 4. Libraries & Versions

### 4.1 Core Dependencies (from `pyproject.toml` / `requirements.txt`)

| Library | Version | Purpose |
|---------|---------|---------|
| `aiogram` | >=3.0.0 | Async Telegram Bot API framework |
| `httpx` | >=0.24.0 | Async HTTP client for Ollama API |
| `python-dotenv` | >=1.0.0 | Environment variable loading |

### 4.2 Test Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| `pytest` | >=7.0.0 | Testing framework |
| `pytest-asyncio` | >=0.21.0 | Async test support |

### 4.3 External Dependencies (Required)

| Component | Version/Model | Purpose |
|-----------|---------------|---------|
| Ollama | Latest | Local LLM runtime |
| qwen2.5:3b | — | Default model (lightweight) |
| qwen3.5:0.8b | — | Lightest & fastest |
| qwen3.5:2b | — | Balanced |
| qwen3.5:4b | — | More accurate |
| gpt-oss:20b | — | Most capable (GPU-intensive) |

---

## 5. Test Suite

### 5.1 Test Files

| File | Coverage | Test Count |
|------|----------|------------|
| `tests/test_bot.py` | MessageHandler | 6 tests |
| `tests/test_llm.py` | OllamaClient, LLMService | 10 tests |

### 5.2 Test Coverage Details

**test_bot.py — MessageHandler Tests:**
1. `test_handle_text_message` — Successful text processing
2. `test_handle_text_message_no_text` — Empty text handling
3. `test_handle_other_content_photo` — Photo ignored
4. `test_handle_other_content_video` — Video ignored
5. `test_handle_other_content_sticker` — Sticker ignored
6. `test_handle_other_content_document` — Document ignored

**test_llm.py — LLM Tests:**

*OllamaClient (5 tests):*
1. `test_generate_response_success` — Normal flow
2. `test_generate_response_timeout` — Timeout exception
3. `test_generate_response_unavailable` — Connection error
4. `test_generate_response_empty` — Empty response
5. `test_generate_response_internal_error` — HTTP error

*LLMService (5 tests):*
1. `test_process_message_success` — Normal flow
2. `test_process_message_timeout` — Fallback on timeout
3. `test_process_message_unavailable` — Fallback on unavailable
4. `test_process_message_empty` — Fallback on empty
5. `test_process_message_internal_error` — Fallback on error

### 5.3 Running Tests

```bash
.venv/bin/pytest tests/ -v
```

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
- Never raises exceptions — always returns fallback string on error
- Fallback responses: "Request timeout", "LLM is unavailable", "Empty response", "Internal error"

### 6.3 MessageHandler Interface

```python
class MessageHandler:
    def __init__(self, llm_service: LLMService)
    async def handle_text_message(self, message: Message, model: str)
    async def handle_other_content(self, message: Message)
```

**Contract:**
- Sends "⏳ Thinking..." notification before processing
- Deletes "Thinking..." message after response
- Splits long responses into 4000-char chunks (Telegram limit)
- Ignores non-text content (photos, videos, files, stickers)

### 6.4 Configuration Interface

```python
class Config:
    telegram_token: str      # Required: TEL_BOT_TOK env var
    ollama_url: str          # Default: http://localhost:11434
    model_name: str          # Default: qwen2.5:3b
    timeout: httpx.Timeout   # Default: read=180s
```

---

## 7. Functionality

### 7.1 User Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message with wallpaper image |
| `/help` | Show bot info and commands |
| `/model` | Display model selection keyboard |

### 7.2 Model Selection

Models displayed with user-friendly names:

| Model | Display Name | Characteristics |
|-------|--------------|-----------------|
| qwen2.5:3b | турба | Default, lightweight |
| qwen3.5:0.8b | турба версия 2 | Lightest, fastest |
| qwen3.5:2b | оптимальная | Balanced |
| qwen3.5:4b | точная | More accurate |
| gpt-oss:20b | умная | Most capable, slowest |

### 7.3 Message Processing

1. User sends text message
2. Bot sends "⏳ Thinking..." notification
3. Message sent to LLM via OllamaClient
4. "Thinking..." message deleted
5. Response split into chunks (if >4000 chars)
6. Each chunk sent as separate message

### 7.4 Error Handling

| Error Type | User Response | Logged |
|------------|---------------|--------|
| Timeout | "Request timeout" | Yes, WARNING |
| Unavailable | "LLM is unavailable" | Yes, WARNING |
| Empty response | "Empty response" | Yes, WARNING |
| Internal error | "Internal error" | Yes, WARNING |
| Unexpected error | "Internal error" | Yes, ERROR + traceback |

---

## 8. File Interactions

### 8.1 Dependency Graph

```
main.py
├── config.py (import)
├── logger.py (import)
├── errors.py (indirect via clients/services)
├── ollama_client.py (import)
├── llm_service.py (import)
├── message_handler.py (import)
└── BotState (internal class)

message_handler.py
├── logger.py (import)
└── llm_service.py (dependency injection)

llm_service.py
├── ollama_client.py (dependency injection)
├── errors.py (import exceptions)
└── logger.py (import)

ollama_client.py
├── errors.py (import exceptions)
└── logger.py (import)
```

### 8.2 Runtime Interaction Flow

```
[User] → Telegram → main.py (polling)
                      ↓
              Dispatcher routes to handler
                      ↓
         ┌────────────┴────────────┐
         ↓                         ↓
   /start, /help,           /model → inline keyboard
   /model callbacks              ↓
         ↓                BotState.current_model updated
   send wallpaper
         ↓
   text message → MessageHandler.handle_text_message()
                      ↓
              LLMService.process_message()
                      ↓
              OllamaClient.generate_response()
                      ↓
              Ollama API (HTTP POST /api/generate)
                      ↓
              Response propagates back up
                      ↓
              Message split & sent to user
```

### 8.3 Configuration Flow

```
Environment (.env)
       ↓
os.getenv() calls
       ↓
Config class (__init__)
       ↓
config instance (singleton)
       ↓
Used by: main.py, ollama_client.py
```

---

## 9. Key Design Decisions

1. **No Database** — Stateless design, no persistence
2. **Polling over Webhook** — Simpler deployment, no HTTPS required
3. **Error Isolation** — LLM errors never crash the bot
4. **Chunked Responses** — Handles long LLM outputs (Telegram 4096 char limit)
5. **Thinking Notification** — UX improvement for slow LLM responses
6. **Model Switching** — In-memory state, per-bot (not per-user)
7. **Structured Logging** — Consistent log format with timestamps

---

## 10. Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TEL_BOT_TOK` | Yes | — | Telegram bot token |
| `OLLAMA_URL` | No | http://localhost:11434 | Ollama API endpoint |
| `MODEL_NAME` | No | qwen2.5:3b | Default model |
| `TIMEOUT_READ` | No | 180 | Read timeout (seconds) |

---

## 11. Entry Points

**Main Entry:**
```bash
python -m app.main
```

**Key Functions:**
- `main()` — Async entry with error handling
- `run_polling()` — Component initialization & polling start
- `register_handlers()` — Routes registration

---

## 12. Limitations

1. No conversation history / context
2. No per-user model selection (shared state)
3. No rate limiting
4. No message queue (direct processing)
5. Model state lost on restart
6. Single-instance only (no horizontal scaling)

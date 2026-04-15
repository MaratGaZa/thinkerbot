# Legacy Warning — ThinkerBot Technical Debt

## Overview

This document outlines technical debt, architectural weaknesses, and areas requiring future refactoring introduced by the stateful conversation history implementation.

---

## 1. Technical Debt

### 1.1 In-Memory History Storage

**Location:** `app/history/history_manager.py`

**Issue:** History is stored in a simple Python dictionary (`Dict[int, List[Message]]`) in process memory.

**Consequences:**
- All conversation history is lost on bot restart
- Cannot scale horizontally (multiple bot instances would have separate histories)
- Memory usage grows linearly with active users

**Future improvement:** Implement persistent storage (SQLite, Redis, or PostgreSQL) with proper connection pooling.

---

### 1.2 Token Counting Accuracy

**Location:** `app/history/history_manager.py::count_tokens()`

**Issue:** Token estimation uses simple word splitting (`len(content.split())`), which is inaccurate for LLM tokenizers.

**Consequences:**
- May underestimate token count for non-English text
- May overestimate for code snippets or technical content
- Could lead to unexpected truncation or missed summarization triggers

**Future improvement:** Integrate a proper tokenizer (e.g., `tiktoken` for GPT-style models or Ollama-specific tokenizer) for accurate counting.

---

### 1.3 Summarization Callback Coupling

**Location:** `app/handlers/message_handler.py::_summarize_callback()`

**Issue:** The summarization callback is defined in MessageHandler but used by HistoryManager, creating tight coupling.

**Consequences:**
- HistoryManager depends on MessageHandler for summarization logic
- Harder to test components in isolation
- Violates single responsibility principle

**Future improvement:** Extract summarization logic into a dedicated `SummarizationService` with clear interfaces.

---

## 2. Architectural Weaknesses

### 2.1 Missing Abstraction Layer

**Location:** `app/handlers/message_handler.py`, `app/services/llm_service.py`

**Issue:** HistoryManager is directly instantiated and passed through dependency injection, but there's no abstraction layer for context management.

**Consequences:**
- Swapping history implementations requires code changes
- No clear interface for "context provider"
- Difficult to add features like per-chat history or thread support

**Future improvement:** Introduce `IContextManager` interface with implementations for different storage backends.

---

### 2.2 System Prompt as Static Class

**Location:** `app/core/system_prompt.py`

**Issue:** System prompt is a static class variable, not configurable per-user or per-conversation.

**Consequences:**
- Cannot customize bot behavior per user
- No support for conversation-specific prompts
- Changing prompt requires code restart

**Future improvement:** Move system prompt to configuration or database, allow per-user overrides.

---

### 2.3 Logging Without Rotation

**Location:** `app/services/llm_service.py::_log_context()`

**Issue:** Context logs are appended to `logs/context.log` without size limits or rotation.

**Consequences:**
- Log file can grow unbounded
- No automatic cleanup of old entries
- May fill disk on long-running deployments

**Future improvement:** Implement log rotation (e.g., `logging.handlers.RotatingFileHandler`) or external log aggregation.

---

## 3. Performance Bottlenecks

### 3.1 Summarization Latency

**Location:** `app/history/history_manager.py::_summarize()`

**Issue:** Summarization triggers an additional LLM call, potentially doubling response time.

**Consequences:**
- User waits for two LLM responses when summarization triggers
- May cause timeout if both calls are slow
- Poor UX during summarization events

**Future improvement:**
- Cache summaries and trigger summarization asynchronously
- Use lighter model for summarization (already implemented, but could be configurable)
- Implement lazy summarization (summarize during idle time)

---

### 3.2 History Lookup Overhead

**Location:** `app/handlers/message_handler.py::_handle_with_history()`

**Issue:** Every message requires copying history list (`history.copy()`) and converting to dict format.

**Consequences:**
- O(n) overhead per message where n = history size
- Memory allocations for large histories
- Could become significant with many concurrent users

**Future improvement:** Use immutable data structures or copy-on-write patterns.

---

### 3.3 Synchronous File I/O for Logging

**Location:** `app/services/llm_service.py::_log_context()`

**Issue:** Context logging uses synchronous file writes in the async handler.

**Consequences:**
- Blocks event loop during file I/O
- Could cause latency spikes under load
- Not truly async-friendly

**Future improvement:** Use `aiofiles` for async file I/O or write to a queue processed by a background worker.

---

## 4. Clean Architecture Violations

### 4.1 Handler Knows About History Implementation

**Location:** `app/handlers/message_handler.py`

**Issue:** MessageHandler directly imports and uses `HistoryManager`, `Message`, and `SystemPromptProvider`.

**Consequences:**
- Business logic (history management) leaks into presentation layer (handler)
- Harder to swap components
- Testing requires mocking multiple dependencies

**Future improvement:** Move history orchestration to a dedicated `ConversationService` layer.

---

### 4.2 LLMService Handles File I/O

**Location:** `app/services/llm_service.py`

**Issue:** LLMService directly writes to filesystem for logging, mixing business logic with infrastructure concerns.

**Consequences:**
- Violates separation of concerns
- Harder to test without file system
- Logging strategy is hardcoded

**Future improvement:** Inject a logger interface (`IContextLogger`) and move file handling to infrastructure layer.

---

## 5. Scalability Concerns

### 5.1 No Horizontal Scaling Support

**Location:** `app/history/history_manager.py`

**Issue:** In-memory storage prevents running multiple bot instances.

**Consequences:**
- Single point of failure
- Cannot handle increased load with multiple instances
- State loss on instance failure

**Future improvement:** Externalize state to Redis or similar shared storage.

---

### 5.2 User Count Memory Growth

**Location:** `app/history/history_manager.py::_storage`

**Issue:** Memory usage is proportional to `user_count × average_history_size`.

**Consequences:**
- Long-running bot with many users may exhaust memory
- No eviction policy for inactive users
- No memory monitoring or alerts

**Future improvement:**
- Implement TTL for inactive users (e.g., clear history after 24 hours)
- Add memory monitoring and graceful degradation
- Implement LRU eviction for least active users

---

## 6. Recommended Future Refactoring

### Priority 1 (High Impact)
1. **Persistent storage** — Migrate from in-memory to Redis/SQLite
2. **Log rotation** — Prevent disk exhaustion from context logs
3. **Async logging** — Use `aiofiles` to avoid blocking event loop

### Priority 2 (Architecture)
4. **Extract ConversationService** — Orchestrate history, summarization, and context building
5. **Introduce IContextManager interface** — Enable swappable storage backends
6. **Inject ILogger interface** — Decouple logging from LLM service

### Priority 3 (Optimization)
7. **Accurate token counting** — Integrate proper tokenizer
8. **Async summarization** — Run summarization in background
9. **Memory monitoring** — Add metrics and alerts for memory usage

---

## 7. What Works Well

Despite the technical debt, the current implementation:
- ✅ Maintains conversation context per user
- ✅ Enforces configurable limits on history size
- ✅ Automatically summarizes when limits are exceeded
- ✅ Logs full context for auditability
- ✅ Preserves backward compatibility (stateless mode via `enable_history` flag)
- ✅ Follows existing code style and patterns

---

## 8. Configuration Reference

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `ENABLE_HISTORY` | `true` | Enable/disable history tracking |
| `HISTORY_MAX_MESSAGES` | `20` | Maximum messages per user |
| `HISTORY_MAX_TOKENS` | `2000` | Maximum token estimate per user |
| `HISTORY_SUMMARIZE_TRIGGER` | `10` | Messages before summarization |

---

*Document generated: 2026-04-15*
*Last updated: Initial stateful implementation*

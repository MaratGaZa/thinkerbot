# chang-request-en.md

## Summary  
The current ThinkerBot processes each Telegram message in isolation, sending only the user’s text to the LLM. To provide context‑aware responses, we propose adding a **stateful history layer** that stores the conversation per user, respects token limits, automatically summarizes when full, injects a system prompt, and logs the full context before each LLM call.

## Objectives  
- **Contextual responses**: Pass all relevant conversation history to the LLM.  
- **Token‑aware limits**: Restrict the number of messages or total token count.  
- **Automatic summarization**: When limits are exceeded, compress history via the LLM itself.  
- **System prompt injection**: Always prepend a fixed system instruction to every request.  
- **Full context logging**: Persist the exact payload sent to the LLM for auditability.

## Scope  
- **Modules affected**: `message_handler.py`, `llm_service.py`, and a new history module.  
- **New components**: `HistoryManager` (in‑memory or file‑backed) and `SystemPromptProvider`.  
- **Non‑changes**: Existing handlers, services, client logic, configuration, and tests remain unchanged.

## Impact Analysis  

| File/Module | Reason for Change | Call Chain Affected | Side Effects |
|-------------|-------------------|---------------------|--------------|
| `app/handlers/message_handler.py` | Must read and update history before calling the service. | handler → history manager → service → client | Adds a read/write operation; potential latency. |
| `app/services/llm_service.py` | Accepts full context, logs it, and triggers summarization. | service → history manager → client | Logic added; public API unchanged. |
| `app/history/history_manager.py` | Stores per‑user history, enforces limits, and initiates summarization. | handler → history manager → service → client | In‑memory storage; memory growth limited by limits. |
| `app/core/system_prompt.py` | Provides a static system prompt. | service → client | Simple data source. |
| `app/clients/ollama_client.py` | No change; remains a pure HTTP client. | – | – |
| Tests (`tests/`) | New tests for history handling, summarization, and logging. | – | Additional test files required. |

**Performance impact**: a small latency increase from history read/write and potential summarization, but reduced request size improves LLM throughput.  
**Memory**: bounded by message/token limits; worst case proportional to `user_count × max_messages`.  
**No regressions**: the original stateless flow remains functional; history layer is optional.

## Current Behavior  
- **Stateless**: Each incoming text message is forwarded separately to the LLM.  
- **No persistence**: Conversation history is lost after each reply.  
- **Error handling**: Only applied to the current message.

## Target Behavior  
- **Stateful**: Before calling LLM, form a context array `[system_prompt] + user_history + current_user_message`.  
- **History storage**: Maintain an ordered list of `{role, content}` per user.  
- **Limit enforcement**: Trim or summarize history when token/message limits are exceeded.  
- **Summarization**: Invoke the LLM with a prompt to summarize older messages, replacing them with a single summary entry.  
- **Logging**: Persist the full context (JSON/YAML) to a log file with timestamp and user ID.

## Data Flow  

### Current  
```
User → Bot (handler) → LLMService.process_message(message_text, model)
        ↘
         OllamaClient.generate_response(prompt=message_text, model=model) → LLM
```

### Proposed  
```
User → Bot (handler)
        |
        v
   HistoryManager.get(user_id)  // retrieves ordered [{role, content}]
        |
        v
   LLMService.prepare_context(system_prompt, history, current_message)
        |
        v
   HistoryManager.update(user_id, {role: "user", content: current_message})
        |
        v
   HistoryManager.check_limits(user_id)  // trim or summarize if needed
        |
        v
   OllamaClient.generate_response(prompt=full_context, model=model) → LLM
        |
        v
   Log full_context to file
```

- **System Prompt** is prepended and never removed.  
- **Limit checks** run before each LLM call to stay within the token budget.  
- **Summarization** replaces old messages with a single summary when limits are hit.

## Technical Design  

### 1. HistoryManager  
- **Storage**: `{user_id: List[Message]}` in memory; optional YAML/JSON persistence.  
- **API**:  
  - `get(user_id) -> List[Message]`  
  - `add(user_id, message: Message)`  
  - `enforce_limits(user_id) -> None` (trim or summarize)  
  - `to_json()` for logging.  

### 2. SystemPromptProvider  
- Returns a static string via `get_prompt()`.  

### 3. Summarization Logic  
- Triggered in `enforce_limits`.  
- Sends a request: `"Summarize the following conversation:" + history` to LLM.  
- Replaces old messages with a single `{role: "assistant", content: summary}`.

### 4. Integration Points  
- **Handler**: fetches/updates history, enforces limits, then passes context to the service.  
- **Service**: receives the array, logs it, and forwards to the client.  
- **Client**: unchanged; receives a string prompt.

### 5. Token Counting  
- Rough estimate: `sum(len(msg.content.split()) for msg in history)`.  
- Configurable threshold (e.g., 2000 tokens).

### 6. Logging Strategy  
- After `enforce_limits`, serialize context to YAML/JSON.  
- Append to `logs/context.log` with timestamp and user ID.

## Context Management Strategy  

1. **Isolated storage**: each user’s history is kept separately by `user_id`.  
2. **Size limit**: configurable maximum messages or tokens; enforced after each addition.  
3. **Auto‑summarization**: when limits are exceeded, older messages are collapsed into a single summary.  
4. **System Prompt**: always added at the start and never removed.

## Summarization Logic  

- **Trigger**: `HistoryManager.enforce_limits` after adding a new message.  
- **Process**:  
  - Concatenate all historical messages (excluding the current one).  
  - Call LLM with prompt: `"Summarize the following conversation into a concise paragraph:"` + history.  
  - Store the summary as `{role: "assistant", content: summary}`.  
- **Replacement**: delete messages older than a set window (e.g., last 5 exchanges) and insert the summary.

## System Prompt Handling  

- Stored in `app/core/system_prompt.py`.  
- Format: `{ "role": "system", "content": "<prompt>" }`.  
- Included as the first element of every context.

## Logging Strategy  

- After `enforce_limits`, serialize entire context to a YAML string.  
- Append to log file `logs/context.log` with format:  
  ```
  [timestamp] user_id=<id> context:
  <YAML>
  ```  
- Manage file size via external rotation or simple size checks.

## Implementation Plan  

| Step | Description | Verification |
|------|-------------|--------------|
| 1 | Create `app/history/history_manager.py` with in‑memory storage and API. | Unit tests for add/get/enforce. |
| 2 | Add `app/core/system_prompt.py` returning a static prompt. | Import in service; test prompt content. |
| 3 | Update `message_handler.py` to retrieve, update, and enforce history before calling the service. | Verify calls to `HistoryManager`. |
| 4 | Modify `llm_service.py` to accept context, log it, and call the client. | Check prompt passed correctly; confirm log entry. |
| 5 | Implement summarization helper inside `HistoryManager`. | Test with artificially long history. |
| 6 | Add configuration for token limits and summarization prompt. | Verify usage of config values. |
| 7 | Create log `logs/context.log` and ensure entries are written. | Confirm file exists after a request. |
| 8 | Write tests for the new history flow, summarization trigger, and logging. | All tests pass. |
| 9 | Optionally update README with new usage notes. | Documentation updated. |

All steps are independent, testable, and preserve existing functionality until integration.

## Risks  

- **Memory**: many users could exhaust RAM; mitigate with strict limits.  
- **Summarization latency**: additional LLM call may double response time; cache or conditional triggers can help.  
- **Token counting accuracy**: word‑split estimate may undercount; a more accurate tokenizer or stricter threshold can reduce risk.  
- **Data loss**: in‑memory history is lost on restart; acceptable for a stateless bot.  
- **Log growth**: context logs can become large; implement rotation.

## Rollback Strategy  

1. **Feature flag**: wrap history logic behind an `enable_history` toggle.  
2. **Gradual rollout**: enable for a subset of users, monitor metrics.  
3. **Revert**: disable the flag to return to stateless behavior; history module can be removed without affecting other components.
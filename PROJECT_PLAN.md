# План разработки ThinkerBot

План составлен на основе истории коммитов проекта (6 коммитов, 2026-04-09 — 2026-04-10)

---

## Этап 1: Базовая реализация (Initial Commit)

**Коммит:** `6c0b8cb` — "Initial commit: ThinkerBot (Telegram bot with local LLM integration)"

### Задачи:
- [x] Создать структуру проекта по SDD (Spec Driven Development)
- [x] Реализовать архитектурные слои:
  - `app/handlers/` — обработка сообщений Telegram
  - `app/services/` — бизнес-логика (LLM service)
  - `app/clients/` — внешние API (Ollama client)
  - `app/core/` — конфигурация, ошибки, логирование
- [x] Настроить асинхронную архитектуру (async/await)
- [x] Реализовать обработку ошибок с fallback-ответами
- [x] Настроить структурированное логирование
- [x] Написать unit-тесты (16 тестов)

### Файлы:
```
app/
├── main.py              # точка входа, polling
├── core/
│   ├── config.py        # конфигурация из .env
│   ├── errors.py        # кастомные исключения
│   └── logger.py        # structured logging
├── handlers/
│   └── message_handler.py
├── services/
│   └── llm_service.py
├── clients/
│   └── ollama_client.py
tests/
├── test_bot.py
└── test_llm.py
```

---

## Этап 2: Исправление таймаутов (Commit #2)

**Коммит:** `7721f05` — "Update timeout configuration for slow LLM models"

### Проблема:
Модели `qwen3.5:4b` и крупнее не успевали генерировать ответ за 30 секунд

### Задачи:
- [x] Увеличить read timeout до 120 секунд
- [x] Использовать `httpx.Timeout` с раздельными настройками:
  - `connect=10.0` — подключение
  - `read=120.0` — чтение ответа (LLM генерация)
  - `write=30.0` — отправка запроса
  - `pool=10.0` — ожидание в пуле
- [x] Добавить переменную окружения `TIMEOUT_READ`
- [x] Исправить конструктор `OllamaClient` для использования `DEFAULT_TIMEOUT`

### Изменённые файлы:
- `app/clients/ollama_client.py`
- `app/core/config.py`
- `.env.example`

---

## Этап 3: Welcome-экран (Commit #3)

**Коммит:** `c6e1db5` — "Add welcome screen with wallpaper and model display names"

### Задачи:
- [x] Добавить команду `/start` с отправкой картинки (`wallpaper.jpg`)
- [x] Добавить команду `/help` с информацией о боте
- [x] Реализовать команду `/model` с inline-клавиатурой
- [x] Создать человеко-читаемые названия моделей:
  | Отображение | Модель |
  |-------------|--------|
  | турба | qwen2.5:3b |
  | турба версия 2 | qwen3.5:0.8b |
  | оптимальная | qwen3.5:2b |
  | точная | qwen3.5:4b |
  | умная | gpt-oss:20b |

### Новые файлы:
- `img/wallpaper.jpg` — приветственная картинка
- `img/icon.jpg` — иконка бота (установлена в Telegram)

### Изменённые файлы:
- `app/main.py` — handlers для `/start`, `/help`, `/model`

---

## Этап 4: Лимит длины сообщений (Commit #4)

**Коммит:** `71df3a7` — "Fix Telegram message length limit issue"

### Проблема:
Telegram ограничивает сообщения 4096 символами

### Задачи:
- [x] Добавить `num_predict: 512` в payload Ollama (позже изменено)
- [x] Реализовать утилиту `split_text()` для разбивки текста
- [x] Отправлять ответы частями при превышении лимита

### Изменённые файлы:
- `app/clients/ollama_client.py`
- `app/handlers/message_handler.py`

---

## Этап 5: UX улучшение (Commit #5)

**Коммит:** `51d3965` — "Add UX improvement: show 'Thinking...' status"

### Задачи:
- [x] Показывать "⏳ Thinking..." перед началом генерации
- [x] Удалять сообщение "Thinking..." после получения ответа
- [x] Улучшить пользовательский опыт (пользователь видит, что бот работает)

### Изменённые файлы:
- `app/handlers/message_handler.py`

---

## Этап 6: Исправление обрезания ответов (Commit #6)

**Коммит:** `71256fd` — "Fix truncated responses: remove num_predict limit"

### Проблема:
`num_predict: 512` обрезал ответы на середине

### Задачи:
- [x] Установить `num_predict: -1` (без ограничений)
- [x] Модель сама решает, когда закончить ответ
- [x] `split_text()` продолжает защищать от лимита Telegram

### Изменённые файлы:
- `app/clients/ollama_client.py`

---

## Итоговая статистика

| Метрика | Значение |
|---------|----------|
| Всего коммитов | 6 |
| Файлов в проекте | 25+ |
| Строк кода (без тестов) | ~500 |
| Unit-тестов | 16 |
| Команд бота | 4 (`/start`, `/help`, `/model`, текстовые сообщения) |
| Моделей LLM | 5 |

---

## Архитектура (итог)

```
┌─────────────┐
│  Telegram   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Bot Handler    │  ← /start, /help, /model, text
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  LLM Service    │  ← error handling, fallbacks
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Ollama Client  │  ← HTTP API, timeout, split_text
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Ollama Server  │  ← локальная LLM
└─────────────────┘
```

---

## Следующие шаги (не реализовано)

- [ ] Rate limiting для пользователей
- [ ] Очередь запросов (asyncio.Queue)
- [ ] Кэширование частых запросов
- [ ] Поддержка контекста диалога
- [ ] Streaming ответов от LLM
- [ ] Админ-панель для статистики

---

*Документ создан: 2026-04-10*
*На основе: git log --reverse*

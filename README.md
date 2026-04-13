# ThinkerBot — Telegram-бот с локальной LLM

Telegram-бот, который принимает текстовые сообщения, отправляет их в локальную LLM (Ollama) и возвращает ответ пользователю.

## Требования

- Python 3.12+
- Ollama с установленной моделями: `qwen2.5:3b`, `qwen3.5:0.8b`, `qwen3.5:2b`, `qwen3.5:4b`, `gpt-oss:20b`.
- Telegram Bot Token

## Установка

### 1. Установка зависимостей

```bash
# Через uv (рекомендуется)
uv pip install -e ".[test]"

# Или через pip
pip install -r requirements.txt
```

### 2. Настройка окружения

Создайте файл `.env` в корне проекта:

```bash
cp .env.example .env
```

Отредактируйте `.env` и укажите ваши параметры:

```env
TEL_BOT_TOK=ваш_токен_telegram_бота
OLLAMA_URL=http://localhost:11434
MODEL_NAME=qwen3.5:4b
TIMEOUT=30
```

### 3. Получение токена Telegram

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен в `.env`

### 4. Установка Ollama и модели

```bash
# Установка Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Установка моделей (рекомендуется начать с лёгкой)
ollama pull qwen2.5:3b       # модель по умолчанию (лёгкая)
ollama pull qwen3.5:0.8b     # самая лёгкая
ollama pull qwen3.5:2b       # лёгкая
ollama pull qwen3.5:4b       # средняя
ollama pull gpt-oss:20b      # тяжёлая (требует мощный GPU)

# Запуск Ollama сервера
ollama serve
```

## Запуск бота

```bash
.venv/bin/python -m app.main
```

## Использование

1. Запустите бота
2. Отправьте текстовое сообщение в Telegram
3. Бот обработает запрос через LLM и вернёт ответ

### Команды

- `/model` — выбрать модель для обработки запросов

**Доступные модели:**
- `qwen2.5:3b` — по умолчанию (рекомендуется)
- `qwen3.5:0.8b` — самая лёгкая и быстрая
- `qwen3.5:2b` — лёгкая
- `qwen3.5:4b` — средняя
- `gpt-oss:20b` — тяжёлая (требует мощный GPU)

## Тесты

```bash
.venv/bin/pytest tests/ -v
```

## Архитектура

```
app/
├── main.py                 # Точка входа, polling
├── core/
│   ├── config.py           # Конфигурация из .env
│   ├── errors.py           # Кастомные исключения
│   └── logger.py           # Structured logging
├── handlers/
│   └── message_handler.py  # Обработка сообщений Telegram
├── services/
│   └── llm_service.py      # LLM сервис с error handling
└── clients/
    └── ollama_client.py    # HTTP клиент для Ollama API
```

## Обработка ошибок

| Сценарий | Ответ бота |
|----------|------------|
| LLM недоступна | "LLM is unavailable" |
| Таймаут | "Request timeout" |
| Пустой ответ | "Empty response" |
| Внутренняя ошибка | "Internal error" |

## Особенности

- Только текстовые сообщения (фото, видео, файлы игнорируются)
- Асинхронная обработка запросов
- Нет хранения истории диалогов
- Нет базы данных
- Работа через polling (не webhook)

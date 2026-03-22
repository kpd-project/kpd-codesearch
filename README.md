# KPD RAG Bot

Telegram-бот и веб-интерфейс для ответов на вопросы о коде с использованием RAG.

## Возможности

- Работа в приватном чате Telegram с белым списком пользователей (`whitelist.json` + fallback из `.env`)
- Индексация нескольких репозиториев (каждый = отдельная коллекция в Qdrant)
- Ответы на вопросы о коде через LLM (OpenRouter)
- Управление репозиториями через бота и Web UI
- Два режима в Telegram: **Two-Agent** (Analyst + Answerer) и **Simple** (агентный `generator.py` или один проход — см. `RAG_RUNTIME_MODE`, `AGENTS.md`)
- Веб-интерфейс на `http://localhost:8000` (FastAPI + React)

## Использование

### Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и инструкция |
| `/list` | Список доступных репозиториев |
| `/add <repo>` | Добавить и проиндексировать репозиторий |
| `/remove <repo>` | Удалить репозиторий |
| `/reindex <repo>` | Переиндексировать репозиторий |
| `/status` | Статус всех коллекций |
| `/mode` | Переключить Two-Agent / Simple (до перезапуска бота) |
| `/adduser <id/@username>` | Добавить пользователя в whitelist |
| `/removeuser <id/@username>` | Удалить пользователя из whitelist |
| `/listusers` | Список пользователей в whitelist |
| `/id` | Узнать свой ID или ID пользователя (reply на сообщение) |
| `<текст>` | Вопрос — RAG запрос |

### Примеры вопросов

- "Как работает авторизация в бэкенде?"
- "Где определена модель пользователя?"
- "Какие API эндпоинты есть для заказов?"

### Режимы работы (Telegram)

| Режим | Описание |
|-------|----------|
| **Two-Agent** | Analyst планирует поиск → Answerer синтезирует ответ |
| **Simple** | Без Two-Agent: либо агентный цикл `generator.py`, либо `simple` (один проход) — см. `RAG_RUNTIME_MODE` в `.env` и `AGENTS.md` |

По умолчанию для Two-Agent: `USE_TWO_AGENT_PIPELINE` в `.env`. Команда `/mode` переопределяет до рестарта.

## Установка

### 1. Клонирование и зависимости

```bash
git clone <repo-url>
cd kpd-codesearch
pip install -r requirements.txt
```

### 2. Настройка .env

Скопируйте `.env.example` в `.env` и заполните. Ключевые переменные:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_WHITELIST_USERS=123456789

# OpenRouter
OPENROUTER_API_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=google/gemini-2.5-flash-preview

# Embeddings (через OpenRouter)
EMBEDDINGS_MODEL=openai/text-embedding-3-small
EMBEDDINGS_DIMENSION=1536

# Qdrant
QDRANT_URL=https://qdrant.gotskin.ru
QDRANT_API_KEY=your_qdrant_key

# Repos (список репо — в Qdrant / UI, не в .env)
REPOS_BASE_PATH=d:/kpd-project

# Режимы
USE_TWO_AGENT_PIPELINE=true
RAG_RUNTIME_MODE=agent
```

Полный список переменных и комментарии — в `.env.example`.

### Whitelist пользователей

Доступ хранится в `whitelist.json` (создаётся автоматически). Если в файле есть непустой список пользователей, он имеет приоритет над `TELEGRAM_WHITELIST_USERS` в `.env`. Управление через команды бота: `/adduser`, `/removeuser`, `/listusers`, `/id`.

### Грамматики Tree-sitter (опционально)

Для Java, Go и др. при первом запуске может потребоваться:

```bash
treesitter-chunker setup grammars java
# или все популярные
treesitter-chunker setup grammars --all
```

Python, JavaScript, TypeScript уже встроены в wheels.

### 3. Запуск

```bash
python main.py
```

Откройте веб-интерфейс: `http://localhost:8000`. Бот запускается параллельно, если задан `TELEGRAM_BOT_TOKEN`.

## Структура проекта

```
kpd-codesearch/
├── .env.example
├── whitelist.json        # Whitelist (опционально)
├── requirements.txt
├── config.py
├── main.py               # Telegram + Web
├── bot/handlers.py
├── web/                  # FastAPI
├── ui/                   # React (Vite)
└── rag/
    ├── chunker/
    ├── embeddings.py
    ├── generator.py
    ├── indexer.py
    ├── qdrant_client.py
    ├── retriever.py
    └── agent/            # Two-Agent pipeline
```

## Требования

- Python 3.11+ (treesitter-chunker)
- Qdrant (удалённый)
- OpenRouter API ключ
- Telegram Bot Token (если нужен бот)

## Лицензия

MIT

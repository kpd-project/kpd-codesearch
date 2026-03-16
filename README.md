# KPD RAG Bot

Telegram-бот для ответов на вопросы о коде с использованием RAG.

## Возможности

- Работа в приватном чате Telegram с белым списком пользователей
- Индексация нескольких репозиториев (каждый = отдельная коллекция в Qdrant)
- Ответы на вопросы о коде с использованием LLM (GLM-4 через OpenRouter)
- Управление репозиториями через команды бота
- Динамическое добавление/удаление/переиндексация репозиториев
- Два режима работы: Two-Agent (двухагентный) и Simple (прямой RAG)

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
| `/mode` | Переключить режим работы (Two-Agent / Simple) |
| `<текст>` | Просто вопрос — RAG запрос |

### Примеры вопросов

- "Как работает авторизация в бэкенде?"
- "Где определена модель пользователя?"
- "Какие API эндпоинты есть для заказов?"

### Режимы работы

Бот поддерживает два режима:

| Режим | Описание |
|-------|----------|
| **Two-Agent** | Двухагентный: Analyst планирует поиск → Answerer синтезирует ответ |
| **Simple** | Одноагентный: прямой RAG через generator.py |

По умолчанию используется Two-Agent режим (настраивается через `USE_TWO_AGENT_PIPELINE` в `.env`).

Переключение: команда `/mode` — показывает inline-кнопки для выбора режима.

## Установка

### 1. Клонирование и зависимости

```bash
git clone <repo-url>
cd lcpro
pip install -r requirements.txt
```

### 2. Настройка .env

Скопируйте `.env.example` в `.env` и заполните:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_WHITELIST_USERS=123456789

# OpenRouter
OPENROUTER_API_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=google/gemini-2.0-flash-001

# Embeddings
EMBEDDINGS_MODEL=text-embedding-3-small
EMBEDDINGS_DIMENSION=1536

# Qdrant
QDRANT_URL=https://qdrant.gotskin.ru
QDRANT_API_KEY=your_qdrant_key

# Repos
REPOS_BASE_PATH=d:/kpd-project
REPOS_WHITELIST=kpd-backend,kpd-frontend,kpd-se,kpd-landing,kpd-pdf-2

# Mode
USE_TWO_AGENT_PIPELINE=true
```

### 3. Грамматики Tree-sitter (опционально)

Для Java, Go и др. (kpd-backend) при первом запуске может потребоваться:

```bash
treesitter-chunker setup grammars java
# или все популярные
treesitter-chunker setup grammars --all
```

Python, JavaScript, TypeScript уже встроены в wheels.

### 4. Запуск

```bash
python main.py
```

## Структура проекта

```
lcpro/
├── .env                  # Конфигурация
├── .env.example          # Шаблон
├── requirements.txt      # Зависимости
├── config.py            # Конфиг
├── main.py              # Точка входа
├── bot/
│   └── handlers.py      # Обработчики команд
└── rag/
    ├── chunker/         # Семантический чанкинг (Tree-sitter + fallback)
    ├── embeddings.py     # Модель эмбедингов
    ├── generator.py     # Генерация ответов
    ├── indexer.py       # Индексация
    ├── qdrant_client.py # Работа с Qdrant
    └── retriever.py     # Поиск по векторам
```

## Требования

- Python 3.11+ (treesitter-chunker)
- Qdrant (удалённый)
- OpenRouter API ключ
- Telegram Bot Token

## Лицензия

MIT

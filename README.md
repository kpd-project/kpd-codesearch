# АСТРА-М CodeSearch (ASTRA-M)

Веб-приложение для ответов на вопросы о коде с использованием RAG (индексация в Qdrant, чат в браузере).

## Возможности

- Индексация нескольких репозиториев (каждый — отдельная коллекция в Qdrant)
- Ответы на вопросы о коде через LLM (OpenAI-compatible API)
- Управление репозиториями в UI: добавление, удаление, переиндексация, описание
- Два режима пайплайна: Two-Agent (аналитик + ответчик) и Simple (прямой RAG)
- Режим RAG в runtime: **простой** (поиск + ответ) или **агент** (инструменты), переключается в настройках

## Использование

После запуска откройте веб-интерфейс (по умолчанию `http://localhost:8000`).

- **Репозитории** — список коллекций, прогресс индексации, добавление папок из `REPOS_BASE_PATH`, карточка репозитория с переиндексацией
- **Чат** — вопросы по проиндексированному коду; ответ приходит потоком (SSE)
- **Настройки** — runtime (модель, температура, режим RAG), системные параметры из `.env` (только просмотр)

### Примеры вопросов

- «Как работает авторизация в бэкенде?»
- «Где определена модель пользователя?»
- «Какие API эндпоинты есть для заказов?»

### Режимы пайплайна (Two-Agent vs Simple)

| Режим | Описание |
|-------|----------|
| **Two-Agent** | Analyst планирует поиск → Answerer синтезирует ответ |
| **Simple** | Одноагентный прямой RAG через `generator.py` |

По умолчанию включён Two-Agent (`USE_TWO_AGENT_PIPELINE` в `.env`).

Режим **RAG в чате** (simple / agent) задаётся в разделе настроек выполнения и через `RAG_RUNTIME_MODE` в `.env`.

## Установка

### 1. Клонирование и зависимости

```bash
git clone <repo-url>
cd astra-m-codesearch
pip install -r requirements.txt
```

### 2. Настройка .env

Скопируйте `.env.example` в `.env` и заполните:

```env
# LLM (OpenAI-compatible: OpenRouter, vLLM, корп. /openai/v1, …)
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=your_key
OPENAI_MODEL=google/gemini-2.0-flash-001

# Embeddings
EMBEDDINGS_MODEL=text-embedding-3-small
EMBEDDINGS_DIMENSION=1536

# Qdrant
QDRANT_URL=https://qdrant.yoursite.ru
QDRANT_API_KEY=your_qdrant_key

# Repos
REPOS_BASE_PATH=d:/projects
REPOS_WHITELIST=backend,frontend,services-pdf

# Mode
USE_TWO_AGENT_PIPELINE=true
```

### 3. Грамматики Tree-sitter (опционально)

Для Java, Go и др. при первом запуске может потребоваться:

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

## Docker Compose: 2 варианта деплоя

Базовый файл `docker-compose.yml` поднимает приложение и использует `QDRANT_URL` из `.env` (обычно облачный Qdrant).

### Вариант A: облачный Qdrant (без локального контейнера)

1) Укажите в `.env`:

```env
QDRANT_URL=https://your-cloud-qdrant
QDRANT_API_KEY=your_key_if_needed
```

2) Запустите:

```bash
docker compose up -d --build
```

### Вариант B: локальный Qdrant в Docker

Используется `docker-compose.local-qdrant.yml` как override:

- поднимается контейнер `qdrant/qdrant`
- имя контейнера Qdrant: `astra-m-qdrant`
- имя volume для данных: `astra-m-qdrant-storage`
- сервис приложения переключается на `QDRANT_URL=http://qdrant:6333`
- порт Qdrant пробрасывается наружу: `6333` (HTTP) и `6334` (gRPC)

Запуск:

```bash
docker compose -f docker-compose.yml -f docker-compose.local-qdrant.yml up -d --build
```

Открыть Qdrant с хоста: `http://localhost:6333`

Остановка:

```bash
docker compose -f docker-compose.yml -f docker-compose.local-qdrant.yml down
```

## Структура проекта

```
astra-m-codesearch/
├── .env                  # Конфигурация (локально)
├── .env.example          # Шаблон
├── requirements.txt
├── config.py             # Конфиг
├── main.py               # Точка входа (uvicorn)
├── web/                  # FastAPI + статика UI
├── frontend/             # Фронтенд (Vite/React)
└── rag/
    ├── chunker/          # Семантический чанкинг (Tree-sitter + fallback)
    ├── embeddings.py
    ├── generator.py
    ├── indexer.py
    ├── qdrant_client.py
    └── retriever.py
```

## Требования

- Python 3.11+ (treesitter-chunker)
- Qdrant (удалённый или в Docker)
- Ключ к LLM (OpenAI-compatible endpoint)

## Лицензия

MIT

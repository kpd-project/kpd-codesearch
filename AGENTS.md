# AGENTS.md

## ЦЕЛЬ ПРОЕКТА

Создание Telegram-бота и веб-интерфейса для закрытого чата: ответы на вопросы о коде из репозиториев проекта ASTRA-M с использованием RAG.

---

## ТЕХНОЛОГИЧЕСКИЙ СТЕК

| Компонент  | Технология                                                                                                                                              |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bot        | python-telegram-bot (polling)                                                                                                                           |
| Web        | FastAPI + uvicorn, фронт в `ui/` (Vite/React)                                                                                                           |
| Vector DB  | Qdrant (remote: qdrant.gotskin.ru)                                                                                                                      |
| Embeddings | `openai/text-embedding-3-small` (через OpenRouter)                                                                                                      |
| LLM        | задаётся в `.env` / Web UI: по умолчанию в коде `google/gemini-2.5-flash-preview` (simple-ветка); Two-Agent — GLM-4 (Analyst/Answerer) через OpenRouter |
| Chunking   | Tree-sitter (`treesitter-chunker`) + построчный fallback                                                                                                |

---

## СТРУКТУРА КОДА

```
astra-m-codesearch/
├── config.py              # Конфигурация из .env
├── main.py                # Точка входа: Telegram (thread) + Web (uvicorn :8000)
├── whitelist.json         # Whitelist пользователей (приоритет над .env, см. config.py)
├── bot/
│   └── handlers.py        # Команды и сообщения Telegram
├── web/
│   ├── main.py            # FastAPI, раздача UI
│   ├── api.py             # REST + SSE (/api/query)
│   └── state.py           # Состояние, runtime-настройки веба
├── ui/                    # React (Vite), kebab-case для файлов
└── rag/
    ├── qdrant_client.py
    ├── embeddings.py
    ├── chunker/           # Tree-sitter + fallback
    ├── indexer.py
    ├── retriever.py
    ├── generator.py       # Агентный RAG (tool loop)
    └── agent/             # Two-Agent pipeline (Analyst + Answerer)
```

---

## АРХИТЕКТУРА

```
User → Telegram или Web UI → RAG Pipeline → OpenRouter (LLM / embeddings)
                              ↑
                        Qdrant (vector search)
                              ↑
                        чанки кода с диска (REPOS_BASE_PATH)
```

Каждый репозиторий — отдельная коллекция в Qdrant.

---

## КОМАНДЫ БОТА

| Команда                                        | Описание                                  | Реализация                    |
| ---------------------------------------------- | ----------------------------------------- | ----------------------------- |
| `/start`                                       | Приветствие                               | `handlers.py:start_command`   |
| `/list`                                        | Список репозиториев                       | `handlers.py:list_command`    |
| `/add <repo>`                                  | Добавить + индекс                         | `handlers.py:add_command`     |
| `/remove <repo>`                               | Удалить                                   | `handlers.py:remove_command`  |
| `/reindex <repo>`                              | Переиндексировать                         | `handlers.py:reindex_command` |
| `/status`                                      | Статус коллекций                          | `handlers.py:status_command`  |
| `/mode`                                        | Two-Agent / Simple (в памяти до рестарта) | `handlers.py:mode_command`    |
| `/adduser`, `/removeuser`, `/listusers`, `/id` | Whitelist                                 | `handlers.py`                 |
| `<текст>`                                      | Вопрос → RAG                              | `handlers.py:handle_message`  |

В группах ответ только при `@бот` или reply на сообщение бота.

---

## РЕЖИМЫ РАБОТЫ

### Telegram: `/mode`

| Режим         | Поведение                                                                                |
| ------------- | ---------------------------------------------------------------------------------------- |
| **Two-Agent** | `rag/agent/pipeline.py`: Analyst → поиск → Answerer                                      |
| **Simple**    | Если `RAG_RUNTIME_MODE=simple` — `generate_simple_answer`; иначе агентный `generator.py` |

- Дефолт Two-Agent/Simple при старте: `USE_TWO_AGENT_PIPELINE` (`.env`).
- Переключение `/mode` хранится в `context.bot_data` (in-memory, сбрасывается при перезапуске).

### Переменная `RAG_RUNTIME_MODE` (`simple` \| `agent`)

Имеет смысл при **Simple** в Telegram и задаёт начальный `rag_mode` для веба (`web/state.py`). Через веб можно менять runtime без рестарта: `PUT /api/config/runtime`.

В веб-чате нет отдельного Two-Agent пайплайна (Analyst/Answerer): только `simple` (поиск + один ответ) или `agent` (агентный цикл в `generator.py`). Двухагентный режим — только в Telegram при выборе Two-Agent в `/mode`.

---

## RAG PIPELINE

### 1. Chunking (`chunker/`)

- **Основной путь**: Tree-sitter — границы по функциям, классам, методам.
- **Fallback**: построчно с перекрытием для неподдерживаемых языков.
- Исключаются: `node_modules`, `.git`, `target`, `dist`, `build` и т.д.

### 2. Embeddings (`embeddings.py`)

- Модель из `EMBEDDINGS_MODEL` (например `openai/text-embedding-3-small`).
- Размерность: `EMBEDDINGS_DIMENSION` (для указанной модели — обычно 1536).

### 3. Indexing (`indexer.py`)

- Коллекция в Qdrant на репозиторий, метаданные: repo, path, language, type и др.

### 4. Retrieval (`retriever.py`)

- Поиск по векторам; фактический `top_k` в агенте ограничен `RAG_SEARCH_TOP_K` / `RAG_SEARCH_TOP_K_MAX` из конфига.

### 5. Generation

- **Two-Agent**: Analyst + Answerer (`rag/agent/`).
- **Simple + agent**: `generator.py` (инструмент `search_code`).
- **Simple + simple**: поиск + один ответ без tool-цикла.

## РАЗРАБОТКА

### Запуск

```bash
pip install -r requirements.txt
python main.py
```

Веб: `http://localhost:8000`. Бот стартует в отдельном потоке, если задан `TELEGRAM_BOT_TOKEN`.

---

## ИМЕНОВАНИЕ ФАЙЛОВ И ПАПОК

### UI (`ui/`)

- Файлы и папки — **kebab-case** (например `repo-card.tsx`).
- Исключения: `.env`, `package.json`, конфиги с собственными соглашениями.

### Backend (Python)

- `snake_case` для файлов и функций.

---

## UI / Темизация (shadcn)

- Компоненты из shadcn (в т.ч. re-export в `ui/src/components/ui/*`).
- Без хардкодной подмены глобальной темы; цвета через CSS-переменные shadcn (`bg-background`, `text-foreground`, и т.д.).
- Допустимы точечные правки разметки/spacing без смены системы тем.

# AGENTS.md

## ЦЕЛЬ ПРОЕКТА

Создание Telegram-бота для закрытого чата, который отвечает на вопросы о коде из репозиториев KPD-проекта с использованием RAG.

---

## ТЕХНОЛОГИЧЕСКИЙ СТЕК

| Компонент | Технология |
|-----------|------------|
| Bot Framework | python-telegram-bot |
| Vector DB | Qdrant (remote: qdrant.gotskin.ru) |
| Embeddings | text-embedding-3-small (OpenRouter) |
| LLM | GLM-4 via OpenRouter |
| Chunking | Построчный с перекрытием |

---

## РЕПОЗИТОРИИ ДЛЯ ИНДЕКСАЦИИ

| Репозиторий | Путь | Назначение |
|-------------|------|------------|
| kpd-backend | d:/kpd-project/kpd-backend | Java/Spring Boot |
| kpd-frontend | d:/kpd-project/kpd-frontend | React/Vite |
| kpd-se | d:/kpd-project/kpd-se | WYSIWYG редактор |
| kpd-landing | d:/kpd-project/kpd-landing | Лендинг |
| kpd-pdf-2 | d:/kpd-project/kpd-pdf-2 | PDF сервис |

---

## СТРУКТУРА КОДА

```
lcpro/
├── config.py              # Конфигурация из .env
├── main.py                # Точка входа, запуск бота
├── bot/
│   └── handlers.py        # Обработчики команд Telegram
└── rag/
    ├── qdrant_client.py   # Работа с Qdrant (коллекции)
    ├── embeddings.py       # Модель эмбедингов
    ├── chunker/            # Семантический чанкинг (Tree-sitter + fallback)
    ├── indexer.py          # Индексация репозитория
    ├── retriever.py        # Поиск по векторам
    └── generator.py        # Генерация ответа через LLM
```

---

## АРХИТЕКТУРА

```
User Message → Telegram Bot → RAG Pipeline → OpenRouter (LLM)
                                       ↑
                                 Vector Search (Qdrant)
                                       ↑
                                 Code Chunks
                                       ↑
                              d:/kpd-project/ repos
```

Каждый репозиторий = отдельная коллекция в Qdrant.

---

## КОМАНДЫ БОТА

| Команда | Описание | Реализация |
|---------|----------|------------|
| `/start` | Приветствие | handlers.py:start_command |
| `/list` | Список репозиториев | handlers.py:list_command |
| `/add <repo>` | Добавить + индекс | handlers.py:add_command |
| `/remove <repo>` | Удалить | handlers.py:remove_command |
| `/reindex <repo>` | Переиндексировать | handlers.py:reindex_command |
| `/status` | Статус коллекций | handlers.py:status_command |
| `/mode` | Переключить режим (Two-Agent / Simple) | handlers.py:mode_command |
| `<текст>` | Вопрос → RAG | handlers.py:handle_message |

---

## РЕЖИМЫ РАБОТЫ

Бот поддерживает два режима обработки вопросов:

| Режим | Описание |
|-------|----------|
| **Two-Agent** | Двухагентный пайплайн: Analyst планирует поиск → Answerer синтезирует ответ |
| **Simple** | Одноагентный пайплайн: прямой RAG (generator.py) |

### Переключение режима

- **Команда `/mode`** — показывает inline-кнопки для выбора режима
- **Дефолт при старте** — берётся из `config.USE_TWO_AGENT_PIPELINE` (`.env`)
- **Хранение** — в `context.bot_data` (in-memory, сбрасывается при перезапуске бота)

---

## RAG PIPELINE

### 1. Chunking (chunker/)
- **Семантика**: Tree-sitter (treesitter-chunker) — границы по функциям, классам, методам (Java, JS, TS, Python, Go, Rust и др.)
- **Fallback**: построчно с перекрытием для неподдерживаемых языков (JSON, YAML, MD и т.д.)
- Исключаются: node_modules, .git, target, dist, build и т.д.

### 2. Embeddings (embeddings.py)
- Модель: text-embedding-3-small
- Размерность: 1536
- Провайдер: OpenRouter API

### 3. Indexing (indexer.py)
- Создание коллекции в Qdrant
- Генерация векторов
- Загрузка точек с метаданными (repo, path, language, type)

### 4. Retrieval (retriever.py)
- Поиск по векторам (top_k=5)
- Сортировка по score

### 5. Generation (generator.py)
- Сбор контекста из результатов
- Формирование промпта
- Запрос к GLM-4 через OpenRouter

---

## НАСТРОЙКИ (.env)

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_WHITELIST_USERS=
OPENROUTER_API_KEY=
OPENROUTER_MODEL=google/gemini-2.0-flash-001
EMBEDDINGS_MODEL=text-embedding-3-small
EMBEDDINGS_DIMENSION=1536
QDRANT_URL=https://qdrant.gotskin.ru
QDRANT_API_KEY=
REPOS_BASE_PATH=d:/kpd-project
REPOS_WHITELIST=kpd-backend,kpd-frontend,kpd-se,kpd-landing,kpd-pdf-2
```

---

## РАЗРАБОТКА

### Запуск
```bash
pip install -r requirements.txt
python main.py
```

### При изменении кода
1. Изменения в .env → перезапуск бота
2. Новый репозиторий → добавить в REPOS_WHITELIST
3. Изменение chunking → переиндексация: /reindex <repo>

### Тесты и линтеры
Пока не настроены. При необходимости добавить pytest/ruff.

---

## ПРИНЯТЫЕ РЕШЕНИЯ

1. **Отдельные коллекции** — каждый репозиторий своя коллекция в Qdrant для гибкого управления
2. **OpenRouter** — единый API для embeddings и LLM
3. **Простой chunking** — построчный с перекрытием, без сложных парсеров
4. **Whitelist пользователей** — для безопасности в закрытом чате

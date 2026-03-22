# Architecture Decisions Log

## [DEC-001] Конфигурация: Web UI vs .env

**Дата:** 2026-03-18  
**Статус:** Принято  
**Автор:** Team

---

### Context

При разработке Web UI возникла дилемма: какие параметры конфигурации выносить в веб-интерфейс, а какие оставить в `.env`?

**Проблема:**
- Хочется настраивать репозитории, модели и параметры через Web UI
- Но некоторые параметры влияют на индексацию и инфраструктуру
- Полная миграция в UI усложняет архитектуру и безопасность

---

### Decision

Разделить параметры на **3 уровня** с разными правами доступа и последствиями:

| Уровень | Параметры | Где настраивать | Перезапуск | Переиндексация |
|---------|-----------|-----------------|------------|----------------|
| **🔴 System** | `TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY`, `QDRANT_URL`, `REPOS_BASE_PATH`, `EMBEDDINGS_MODEL`, `EMBEDDINGS_DIMENSION` | **Только .env** | ✅ Требуется | ✅ При смене модели |
| **🟡 Operational** | `REPOS_WHITELIST`, `TELEGRAM_WHITELIST_USERS` | **Web UI (Admin)** | ❌ Не требуется | ⚠️ При добавлении репо |
| **🟢 Runtime** | `OPENROUTER_MODEL` (LLM), `TEMPERATURE`, `TOP_K`, `MAX_CHUNKS` | **Web UI (Все пользователи)** | ❌ Не требуется | ❌ Не требуется |

---

### Rationale

1. **Безопасность:** API keys и токены не должны быть доступны через UI (риск утечки, CSRF)
2. **Влияние на индексацию:**
   - Смена embedding-модели → новая размерность векторов → ломает Qdrant коллекцию
   - Смена LLM модели → только промпт меняется, без последствий
3. **YAGNI:** Системные параметры меняются редко (раз в 3-6 месяцев), UI для них — оверинжиниринг
4. **UX:** Разработчики хотят быстро тестить разные LLM и добавлять репозитории без редактирования файлов

---

### Consequences

#### ✅ Положительные
- Критичные секреты защищены в `.env`
- Runtime-параметры меняются мгновенно через UI
- Простая реализация (не нужно шифровать/валидировать API keys в UI)

#### ⚠️ Отрицательные
- Для смены embeddings model нужно:
  1. Edit `.env`
  2. Restart container
  3. Run `/reindex all`
- Два места конфигурации (может вызвать путаницу)

---

### Implementation Tasks

Создать в Web UI следующие секции:

```
Priority: High
┌─────────────────────────────────────────────────────────────┐
│ Task: Runtime Settings Panel                                │
│ Files: web/static/index.html, web/api.py                    │
│ Endpoints: GET /api/config, PUT /api/config/runtime         │
│ ─────────────────────────────────────────────────────────── │
│ - LLM Model dropdown (список из config.py)                 │
│ - Temperature slider (0.0 - 2.0)                            │
│ - Top-K input (1 - 10)                                      │
│ - [Apply] button → сохраняет в global state                 │
└─────────────────────────────────────────────────────────────┘

Priority: High
┌─────────────────────────────────────────────────────────────┐
│ Task: Repository Management Panel                           │
│ Files: web/static/index.html, web/api.py                    │
│ Endpoints: GET /api/repos, POST /api/repos, DELETE /api/re...│
│ ─────────────────────────────────────────────────────────── │
│ - Список репозиториев с чекбоксами (enabled/disabled)       │
│ - Кнопки: [Reindex], [Remove] для каждого                   │
│ - Кнопка: [+ Add Custom Repo] (модальное окно)              │
│ - Warning при добавлении: "Начнётся индексация..."          │
└─────────────────────────────────────────────────────────────┘

Priority: Medium
┌─────────────────────────────────────────────────────────────┐
│ Task: System Settings Info Panel                            │
│ Files: web/static/index.html                                │
│ ─────────────────────────────────────────────────────────── │
│ - Показать текущие значения (только чтение)                 │
│ - Link: "Edit in .env" → показывает инструкцию              │
│ - Warning: "Требуется рестарт контейнера"                   │
└─────────────────────────────────────────────────────────────┘

Priority: Low (Future)
┌─────────────────────────────────────────────────────────────┐
│ Task: Embeddings Model Changer with Reindex Warning         │
│ Files: web/static/index.html, web/api.py, rag/indexer.py    │
│ ─────────────────────────────────────────────────────────── │
│ - Dropdown с доступными моделями                            │
│ - При смене: modal "Это потребует полной переиндексации!"   │
│ - Кнопка: [Change & Reindex All]                            │
│ - Background task: пересоздать коллекции → индексировать    │
└─────────────────────────────────────────────────────────────┘
```

---

### Validation

Как проверить корректность решения:

1. **Runtime settings:**
   ```bash
   # Изменить LLM через UI → сделать запрос
   curl -X PUT /api/config/runtime -d '{"model": "gemini-2.0-flash"}'
   curl -X POST /api/query -d '{"query": "..."}'
   # Ожидается: ответ от новой модели
   ```

2. **Repository management:**
   ```bash
   # Добавить репо через UI → проверить Qdrant
   curl -X POST /api/repos -d '{"name": "kpd-new"}'
   # Ожидается: коллекция создана, идёт индексация
   ```

3. **System settings:**
   ```bash
   # Изменить .env → рестарт → проверить
   docker-compose down
   # Edit .env: EMBEDDINGS_MODEL=...
   docker-compose up -d
   # Ожидается: старые коллекции несовместимы (ошибка или авто-реиндекс)
   ```

---

### Related Documents

- [`PROJECT_OVERVIEW.md`](./PROJECT_OVERVIEW.md) — общая архитектура
- [`AGENTS.md`](./AGENTS.md) — RAG pipeline детали
- [`.env.example`](./.env.example) — список всех параметров

---

## [DEC-002] Shared State: In-Memory Dict вместо Redis

**Дата:** 2026-03-18  
**Статус:** Принято  
**Автор:** Team

---

### Context

Для синхронизации статуса индексации между Telegram Bot и Web UI нужно общее хранилище состояния.

**Варианты:**
1. Redis (внешнее хранилище)
2. In-Memory Dict (в памяти процесса)

---

### Decision

Использовать **In-Memory Dict** в качестве shared state.

```python
# global state module
indexing_state = {
    "kpd-backend": {"status": "indexing", "progress": 45, "updated_at": "..."},
    "kpd-frontend": {"status": "done", "progress": 100, "updated_at": "..."},
}

# Bot и Web API читают/пишут в один dict
```

---

### Rationale

| Критерий | Redis | In-Memory | Решение |
|----------|-------|-----------|---------|
| **Сложность** | +1 контейнер, коннекты | Просто dict | ✅ In-Memory |
| **Производительность** | ~1-5ms (сеть) | ~0.001ms (RAM) | ✅ In-Memory |
| **Масштабирование** | ✅ Несколько реплик | 🔴 Один процесс | YAGNI сейчас |
| **Персистентность** | ✅ Сохраняется | 🔴 Теряется | Не критично |

**Почему In-Memory достаточно:**
- Один Docker-контейнер (нет реплик)
- Статус индексации не критичен (потеря → просто показать "unknown")
- Упрощает docker-compose (не нужен redis service)

---

### Consequences

#### ✅ Положительные
- Простая реализация (global dict + locks)
- Нет зависимостей (Redis не нужен)
- Быстрый доступ (без сетевых вызовов)

#### ⚠️ Отрицательные
- При рестарте контейнера теряется статус (не критично)
- Нельзя масштабировать на N контейнеров (потом добавим Redis)

---

### Implementation Tasks

```
Priority: High
┌─────────────────────────────────────────────────────────────┐
│ Task: Create state module                                   │
│ Files: web/state.py                                         │
│ ─────────────────────────────────────────────────────────── │
│ - Global dict: indexing_state                               │
│ - Thread-safe access (asyncio.Lock)                         │
│ - Methods: get_status(), update_status(), list_statuses()   │
│ - WebSocket broadcast: notify subscribed clients            │
└─────────────────────────────────────────────────────────────┘

Priority: High
┌─────────────────────────────────────────────────────────────┐
│ Task: WebSocket endpoint for real-time updates              │
│ Files: web/api.py                                           │
│ Endpoints: WS /ws/state                                     │
│ ─────────────────────────────────────────────────────────── │
│ - Accept WebSocket connections                              │
│ - Send JSON state updates on changes                        │
│ - Handle disconnects gracefully                             │
└─────────────────────────────────────────────────────────────┘

Priority: Future (если понадобится масштабирование)
┌─────────────────────────────────────────────────────────────┐
│ Task: Migrate to Redis                                      │
│ Files: web/state.py, docker-compose.yml                     │
│ ─────────────────────────────────────────────────────────── │
│ - Добавить redis-service в docker-compose                   │
│ - Заменить dict на Redis (redis-py)                         │
│ - Pub/Sub для WebSocket broadcast                           │
└─────────────────────────────────────────────────────────────┘
```

---

### Validation

```bash
# 1. Запустить индексацию через Telegram
/reindex kpd-backend

# 2. Открыть Web UI → увидеть прогресс в реальном времени
# Ожидается: прогресс-бар обновляется без refresh

# 3. Запустить индексацию через Web UI
# 2. Проверить Telegram → бот присылает статус
# Ожидается: статусы синхронизированы
```

---

### Related Documents

- [`PROJECT_OVERVIEW.md`](./PROJECT_OVERVIEW.md) — архитектура
- [`main.py`](./main.py) — точка входа (bot + web)

---

## [DEC-003] Vector Database: Оставить Qdrant

**Дата:** 2026-03-18  
**Статус:** Принято  
**Автор:** Team

---

### Context

При планировании Docker + Web UI возник вопрос: стоит ли рассматривать альтернативы Qdrant для векторного поиска?

**Текущее состояние:**
- Qdrant remote уже работает (qdrant.gotskin.ru)
- 5 репозиториев для индексации
- ~10K-100K чанков кода (оценочно)
- Embeddings: text-embedding-3-small (1536 dim)

**Вопрос:** Может ли другая векторная БД дать преимущества в простоте, производительности или стоимости?

---

### Decision

**Оставить Qdrant.** Не рассматривать альтернативы до появления конкретных проблем.

---

### Rationale

#### Рассмотренные альтернативы:

| Векторная БД | Плюсы | Минусы | Вердикт |
|--------------|-------|--------|---------|
| **Qdrant** (текущая) | Rust, быстрая, фильтрация, cloud, remote готов | Отдельный сервис | ✅ **Оптимально** |
| **Chroma** | Embedded (нет сервера), простой API | Медленнее, нет cloud, хуже production | ⚠️ Хуже |
| **pgvector** | В Postgres, ACID, JOINы | Нужен Postgres, медленнее | ⚠️ Нет Postgres |
| **Weaviate** | Гибридный поиск, модули | Тяжелее, сложнее, оверкилл | ⚠️ Избыточно |
| **FAISS** | Очень быстрый (Facebook) | Low-level, нет persistence | ❌ Не подходит |
| **Pinecone** | Managed service, легко | Платный, vendor lock-in | ❌ Дорого |
| **Milvus** | Масштабируемый | Сложный, оверкилл | ❌ Избыточно |

#### Почему Qdrant оптимален для этого проекта:

1. **Уже работает** — remote инстанс настроен и доступен
2. **Производительность** — Rust + SIMD, достаточно для 100K+ векторов
3. **Простота** — один сервис, Python-клиент, понятный API
4. **Функции** — фильтрация по payload, коллекции, scoring
5. **Бесплатно** — свой remote сервер, нет vendor lock-in
6. **Масштабируемость** — если понадобится, есть Qdrant Cloud

#### Архитектурное соответствие:

```
current:
┌─────────────┐      ┌─────────────┐
│   App       │ ───► │  Qdrant     │
│ (Docker)    │      │  (remote)   │
└─────────────┘      └─────────────┘

with Chroma:
┌─────────────┐
│   App       │
│ (Docker)    │  ./db/chroma  ← volume
└─────────────┘
# Минусы: нет remote, сложнее бэкапы

with pgvector:
┌─────────────┐      ┌─────────────┐
│   App       │ ───► │  Postgres   │
│ (Docker)    │      │  + pgvector │
└─────────────┘      └─────────────┘
# Минусы: нужен Postgres, тяжелее
```

---

### Consequences

#### ✅ Положительные
- Не нужно переписывать `rag/qdrant_client.py`
- Не нужно поднимать новую инфраструктуру (Postgres, etc.)
- Стабильность (Qdrant уже протестирован)
- Миграция не потребуется

#### ⚠️ Отрицательные
- Зависимость от remote сервера (qdrant.gotskin.ru)
- Если remote упадёт — нужен fallback
- Не используем преимущества pgvector (если бы был Postgres)

#### 🔧 Митигация рисков
- Добавить health check Qdrant в `/api/health`
- Логировать ошибки подключения
- Иметь backup план (локальный Qdrant в Docker)

---

### Implementation Tasks

```
Priority: Low (если понадобится)
┌─────────────────────────────────────────────────────────────┐
│ Task: Qdrant Health Check                                   │
│ Files: web/api.py, rag/qdrant_client                        │
│ ─────────────────────────────────────────────────────────── │
│ - GET /api/health → проверяет подключение к Qdrant          │
│ - Возвращает: {"qdrant": "ok" | "error", "latency_ms": N}  │
│ - Логировать ошибки подключения                             │
└─────────────────────────────────────────────────────────────┘

Priority: Low (если понадобится)
┌─────────────────────────────────────────────────────────────┐
│ Task: Local Qdrant Fallback                                 │
│ Files: docker-compose.yml, config.py                        │
│ ─────────────────────────────────────────────────────────── │
│ - Опциональный service: qdrant (docker)                     │
│ - Переключатель: QDRANT_URL=local или remote                │
│ - Для development / fallback                                │
└─────────────────────────────────────────────────────────────┘
```

---

### Validation

Как проверить что Qdrant подходит:

```bash
# 1. Проверить подключение
curl https://qdrant.gotskin.ru/api/cluster/status \
  -H "Authorization: Bearer ${QDRANT_API_KEY}"

# 2. Проверить размер коллекций
curl https://qdrant.gotskin.ru/collections \
  -H "Authorization: Bearer ${QDRANT_API_KEY}"

# 3. Проверить latency
time curl -X POST https://qdrant.gotskin.ru/collections/kpd-backend/points/search \
  -H "Authorization: Bearer ${QDRANT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"vector": [...], "limit": 5}'

# Ожидается: < 500ms для поиска
```

**Критерии для пересмотра решения:**
- Latency > 1s регулярно
- Downtime > 1% времени
- Стоимость cloud > $X/мес (если перейдём на managed)
- Потребуется гибридный поиск (векторы + full-text)

---

### Related Documents

- [`PROJECT_OVERVIEW.md`](./PROJECT_OVERVIEW.md) — архитектура с Qdrant
- [`rag/qdrant_client.py`](./rag/qdrant_client.py) — текущая реализация
- [Qdrant Docs](https://qdrant.tech/documentation/) — официальная документация

---

## [DEC-004] Code Graph MCP: ast-grep + SQLite для структурного поиска

**Дата:** 2026-03-18  
**Статус:** Принято  
**Автор:** Team

---

### Context

**Проблема:** У нас 5 репозиториев (Java, TypeScript, Python). Существующий RAG-поиск (векторный через Qdrant) плохо справляется с:

1. Точным структурным поиском (найти класс `UserService`)
2. Связями между языками (какой TS-клиент вызывает Java-эндпоинт?)
3. Запросами по синтаксису (все `@GetMapping`, все `interface`)

**Текущее состояние:**
- RAG (Qdrant) — векторный поиск (~70-80% точность)
- Chunking — построчный с перекрытием (tree-sitter fallback)
- Нет связей Java ↔ TypeScript

**Вопрос:** Как дать ИИ понимание структуры кода, а не только семантики?

---

### Decision

Добавить **Code Graph MCP** — слой структурного поиска на базе `ast-grep` + SQLite.

**Архитектура:**
```
Репозитории → ast-grep → SQLite → MCP Server → ИИ
   (Java, TS)   (AST)     (индекс)  (API)      (Cursor/Claude/Бот)
```

**Компоненты:**

| Компонент | Назначение | Технология |
|-----------|------------|------------|
| **ast-grep** | Сканирование, извлечение символов (AST) | Rust CLI |
| **SQLite** | Индекс символов + связей | Файл (один контейнер) |
| **Indexer** | Запуск ast-grep → запись в SQLite | Python скрипт |
| **Linker** | Связка Java↔TS через OpenAPI spec | Python скрипт |
| **MCP Server** | API для ИИ (5-7 методов) | FastAPI routes |

---

### Rationale

#### Рассмотренные альтернативы:

| Вариант | Плюсы | Минусы | Вердикт |
|---------|-------|--------|---------|
| **SQLite** | Быстро (индексы), JOIN, один файл, ACID | Зависимость (sqlite3), схема | ✅ **Оптимально** |
| **JSONL** | Нет зависимостей, просто | Медленно (O(n)), нет JOIN | ⚠️ Для прототипа |
| **In-Memory Dict** | Очень быстро, просто | Теряется при рестарте | ⚠️ Для dev |
| **Qdrant only** | Одна БД | Нет LIKE, нет JOIN | ❌ Не подходит |

**Почему SQLite оптимален:**
1. **Не сервер** — один файл (`./data/index.db`), нет контейнера
2. **Read-heavy** — читаем часто, пишем редко (при индексации)
3. **JOIN для API linking** — критично для связи Java↔TS
4. **Стандарт** — встроен в Python (`import sqlite3`)

---

### Consequences

#### ✅ Положительные

| benefit | Описание |
|---------|----------|
| **Точность 95%** | AST-поиск понимает синтаксис, а не текст |
| **Скорость <100ms** | SQLite индексы для мгновенного поиска |
| **Java↔TS связи** | Через OpenAPI spec → таблица `api_links` |
| **0 новых сервисов** | SQLite = файл, ast-grep = CLI |
| **Дополняет RAG** | Не заменяет Qdrant, а работает параллельно |

#### ⚠️ Отрицательные

| Risk | Митигация |
|------|-----------|
| Индекс устаревает | Инкрементальная индексация (git diff) |
| Сложность правил | YAML-правила проще чем парсер на Python |
| Нет графа вызовов | CodeQL слишком сложен, ast-grep — золотая середина |

---

### Architecture Update

**Общая схема v3.0:**

```
┌─────────────────────────────────────────────────────────────┐
│                    KPD CodeSearch v3.0                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────────┐                     │
│  │  Telegram   │    │   Web UI        │                     │
│  │     Bot     │    │ (FastAPI + WS)  │                     │
│  └──────┬──────┘    └────────┬────────┘                     │
│         │                    │                               │
│         └────────────┬───────┘                               │
│                      │                                       │
│             ┌────────▼────────┐                              │
│             │  Query Router   │  ← Решает: куда отправить   │
│             └────────┬────────┘                              │
│                      │                                       │
│      ┌───────────────┴───────────────┐                       │
│      │                               │                       │
│ ┌────▼─────┐                 ┌──────▼──────┐                 │
│ │   RAG    │                 │  CodeGraph  │                 │
│ │ Pipeline │                 │     MCP     │                 │
│ │          │                 │             │                 │
│ │ - Qdrant │                 │ - ast-grep  │                 │
│ │ - Vector │                 │ - SQLite    │                 │
│ │ - LLM    │                 │ - Linker    │                 │
│ └──────────┘                 └─────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

**Query Router логика:**

| Тип запроса | Маршрут | Пример |
|-------------|---------|--------|
| Смысл («как работает аутентификация?») | → RAG | Векторный поиск |
| Структура («где класс UserService?») | → MCP | LIKE '%UserService%' |
| Связи («кто вызывает /api/users?») | → MCP | JOIN api_links |
| Неизвестно | → оба + merge | «покажи сервис пользователей» |

---

### Implementation Tasks

```
Priority: P0
┌─────────────────────────────────────────────────────────────┐
│ Task: ast-grep Rules                                        │
│ Files: rules/java-class.yml, rules/java-api.yml,            │
│        rules/ts-export.yml                                   │
│ ─────────────────────────────────────────────────────────── │
│ - 5-7 YAML правил (Java классы, методы, @GetMapping,       │
│   TS экспорты, интерфейсы)                                  │
│ - Тестирование через `sg scan --rule ...`                   │
└─────────────────────────────────────────────────────────────┘

Priority: P0
┌─────────────────────────────────────────────────────────────┐
│ Task: SQLite Indexer                                        │
│ Files: scripts/indexer.py                                   │
│ ─────────────────────────────────────────────────────────── │
│ - Запуск ast-grep → парсинг JSON → SQLite                   │
│ - Таблица: symbols (file, line, language, kind, name, ...)  │
│ - Инкрементальная индексация (git diff)                     │
└─────────────────────────────────────────────────────────────┘

Priority: P1
┌─────────────────────────────────────────────────────────────┐
│ Task: OpenAPI Linker                                        │
│ Files: scripts/linker.py                                    │
│ ─────────────────────────────────────────────────────────── │
│ - Парсинг swagger.json                                      │
│ - Связка Java endpoint ↔ TS client                          │
│ - Таблица: api_links (java_id, ts_id, path)                 │
└─────────────────────────────────────────────────────────────┘

Priority: P1
┌─────────────────────────────────────────────────────────────┐
│ Task: MCP Server API                                        │
│ Files: web/mcp/*.py                                         │
│ ─────────────────────────────────────────────────────────── │
│ - search_symbol(name, kind, language)                       │
│ - find_api_usage(path)                                      │
│ - get_file_content(path)                                    │
│ - deep_structural_search(pattern, language)                 │
└─────────────────────────────────────────────────────────────┘

Priority: P1
┌─────────────────────────────────────────────────────────────┐
│ Task: Query Router                                          │
│ Files: rag/router.py                                        │
│ ─────────────────────────────────────────────────────────── │
│ - Классификация запроса (векторный vs структурный)          │
│ - Маршрутизация: RAG → Qdrant или MCP → SQLite              │
│ - Merge результатов если нужно                              │
└─────────────────────────────────────────────────────────────┘

Priority: P2
┌─────────────────────────────────────────────────────────────┐
│ Task: Docker Integration                                    │
│ Files: Dockerfile, docker-compose.yml                       │
│ ─────────────────────────────────────────────────────────── │
│ - ast-grep CLI в образ                                      │
│ - Volume для SQLite (./data/index.db)                       │
│ - Entry point: indexer → bot + web                          │
└─────────────────────────────────────────────────────────────┘
```

---

### Validation

**Сценарии проверки:**

```bash
# 1. Структурный поиск (MCP)
curl -X POST http://localhost:8000/api/mcp/search_symbol \
  -d '{"name": "UserService", "kind": "class"}'
# Ожидается: список классов за <100ms

# 2. API linking (Java → TS)
curl -X POST http://localhost:8000/api/mcp/find_api_usage \
  -d '{"path": "/api/users"}'
# Ожидается: Java controller + TS компоненты

# 3. Интеграция с ботом
# В Telegram: @GetMapping("/orders")
# Ожидается: 3 места (Java + TS + SE)

# 4. Cursor/Claude MCP
# В IDE чат: "Покажи все @Service классы"
# Ожидается: точный список из SQLite
```

**Метрики:**
- Поиск символов: <100ms
- API linking: <200ms
- Индексация (полная): <5 мин
- Индексация (инкрементальная): <30 сек

---

### Related Documents

- [`PROJECT_OVERVIEW.md`](./PROJECT_OVERVIEW.md) — общая архитектура v3.0
- [`ARCHITECTURE_DECISIONS.md`](./ARCHITECTURE_DECISIONS.md) — DEC-001, DEC-002, DEC-003
- [ast-grep Docs](https://ast-grep.github.io/) — официальная документация
- [MCP Protocol](https://modelcontextprotocol.io/) — спецификация MCP

---

## changelog

- **2026-03-18:** Добавлены DEC-001 (конфигурация), DEC-002 (shared state), DEC-003 (Qdrant), **DEC-004 (Code Graph MCP)**

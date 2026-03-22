# Спецификация Web-интерфейса KPD CodeSearch

## 1. Цель и Назначение

Web-интерфейс предназначен для локального запуска на компьютере разработчика и объединяет четыре функции:

1. **Дашборд мониторинга** — статистика коллекций, количество чанков, статус индексации
2. **Панель управления** — добавление/удаление репозиториев, запуск переиндексации
3. **Web-чат** — интерфейс для вопросов о коде (альтернатива Telegram)
4. **Real-time обновления** — WebSocket для отображения статуса индексации

---

## 2. Технологический Стек

| Компонент | Технология |
|-----------|-------------|
| Web Framework | FastAPI |
| Frontend | React + TypeScript + Vite (`ui/`) |
| Real-time | WebSocket (`/ws/state`) |
| State | In-Memory Dict (DEC-002) |
| Containerization | Docker + docker-compose |

---

## 3. UI/UX Спецификация

### 3.1 Макет страницы

```
┌─────────────────────────────────────────────────────────────────┐
│  Header: "KPD CodeSearch"    [Status: ●]    [Settings] [Help]  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐  ┌─────────────────────────┐ │
│  │     Sidebar (репозитории)    │  │    Main Content Area    │ │
│  │                             │  │                         │ │
│  │  ☑ kpd-backend    [R] [X]   │  │  Tab: [Chat] [Dashboard]│ │
│  │  ☑ kpd-frontend    [R] [X]   │  │                         │ │
│  │  ☐ kpd-se         [R] [X]   │  │  (content based on tab) │ │
│  │  ☐ kpd-landing    [R] [X]   │  │                         │ │
│  │  ☐ kpd-pdf-2     [R] [X]   │  │                         │ │
│  │                             │  │                         │ │
│  │  [+ Add Repository]        │  │                         │ │
│  └─────────────────────────────┘  └─────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Footer: Version 2.0 | Qdrant: Connected | Uptime: HH:MM:SS    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Цветовая схема

| Элемент | Цвет |
|---------|------|
| Background | `#1a1b26` (dark) |
| Surface | `#24283b` |
| Primary | `#7aa2f7` (blue) |
| Success | `#9ece6a` (green) |
| Warning | `#e0af68` (yellow) |
| Error | `#f7768e` (red) |
| Text Primary | `#c0caf5` |
| Text Secondary | `#565f89` |

### 3.3 Компоненты

- **Status Indicator**: зелёный (подключено), жёлтый (индексация), красный (ошибка)
- **Progress Bar**: для отображения прогресса индексации
- **Repository Card**: название, статус, кнопки [Reindex] [Remove]
- **Chat Message**: user/assistant с подсветкой кода
- **Settings Modal**: dropdown, sliders, inputs

---

## 4. Функциональная Спецификация

### 4.1 Дашборд мониторинга

```
Метрики:
├── Total Repositories: N
├── Total Chunks: N
├── Indexing Progress: {repo: progress%}
├── Last Index Time: timestamp
└── Qdrant Status: Connected/Error

Графики (простые, CSS):
├── Bar chart: chunks per repo
└── Activity: recent queries
```

### 4.2 Панель управления

| Функция | Описание |
|---------|----------|
| Repository List | Список с чекбоксами (enabled/disabled) |
| Add Repo | Кнопка → модальное окно (имя + путь) |
| Reindex | Кнопка → запуск индексации в фоне |
| Remove | Кнопка → удаление коллекции из Qdrant |
| Settings | Runtime параметры (LLM, Temperature, Top-K) |

### 4.3 Web-чат

```
Интерфейс:
├── Input field (multiline)
├── [Send] button
├── [Clear] button
└── Code syntax highlighting (highlight.js)

Поведение:
├── Enter = отправить (Shift+Enter = newline)
├── Streaming ответ (поchunk'ам)
├── Копирование кода
└── Markdown render
```

### 4.4 Real-time обновления (WebSocket)

```javascript
// События от сервера
{ "type": "index_progress", "repo": "kpd-backend", "progress": 45 }
{ "type": "index_complete", "repo": "kpd-backend", "chunks": 1234 }
{ "type": "index_error", "repo": "kpd-backend", "error": "..." }
{ "type": "status_change", "qdrant": "connected" }
```

---

## 5. Конфигурация (DEC-001)

Три уровня параметров:

| Уровень | Параметры | Интерфейс |
|---------|-----------|-----------|
| 🔴 System | `TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY`, `QDRANT_URL`, `EMBEDDINGS_MODEL` | Только `.env` |
| 🟡 Operational | Репозитории (коллекции Qdrant), whitelist пользователей | Web UI / бот |
| 🟢 Runtime | `OPENROUTER_MODEL`, `TEMPERATURE`, `TOP_K`, `MAX_CHUNKS` | Web UI (все) |

**Runtime Settings UI:**
- LLM Model dropdown (список из config.py)
- Temperature slider (0.0 - 2.0)
- Top-K input (1 - 10)
- Max Chunks input (1 - 20)

---

## 6. API Endpoints

### 6.1 Основные

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/` | HTML страница |
| GET | `/static/*` | Статические файлы |

### 6.2 RAG

| Method | Endpoint | Описание |
|--------|----------|----------|
| POST | `/api/query` | RAG-запрос (streaming) |

### 6.3 Управление репозиториями

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/api/repos` | Список репозиториев |
| POST | `/api/repos` | Добавить репозиторий |
| DELETE | `/api/repos/{name}` | Удалить репозиторий |
| POST | `/api/repos/{name}/reindex` | Переиндексировать |

### 6.4 Конфигурация

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/api/config` | Текущая конфигурация |
| PUT | `/api/config/runtime` | Изменить runtime параметры |

### 6.5 Мониторинг

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/api/status` | Статус системы |
| GET | `/api/health` | Health check |

### 6.6 WebSocket

| Endpoint | Описание |
|----------|----------|
| `/ws/state` | Real-time обновления |

---

## 7. Безопасность

- **Локальный запуск** — доступ только `localhost:8000`
- **Whitelist пользователей** — для Telegram (не требуется для Web UI)
- **API Keys** — только в `.env`, не в UI
- **CORS** — только localhost

---

## 8. Поток Данных

```
User Input → FastAPI → Query Router
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
       RAG Pipeline   CodeGraph MCP   Response
          │               │               │
          ▼               ▼               ▼
      Qdrant          SQLite         User (WS)
```

---

## 9. Критерии Приёмки

### 9.1 Дашборд
- [ ] Показывает список репозиториев из Qdrant
- [ ] Показывает количество чанков в каждой коллекции
- [ ] Показывает статус подключения к Qdrant

### 9.2 Панель управления
- [ ] Можно добавить репозиторий (появляется в списке)
- [ ] Можно удалить репозиторий (удаляется из Qdrant)
- [ ] Можно запустить переиндексацию (прогресс в реальном времени)
- [ ] Runtime настройки применяются без перезагрузки

### 9.3 Web-чат
- [ ] Отправка сообщения возвращает ответ от LLM
- [ ] Код в ответе подсвечивается
- [ ] Streaming ответ (не ждать полностью)

### 9.4 Real-time
- [ ] WebSocket подключается автоматически
- [ ] Прогресс индексации обновляется без refresh
- [ ] Статус Qdrant обновляется при изменении

---

## 10. Структура Файлов

```
web/
├── api.py              # FastAPI endpoints
├── state.py            # In-memory state management
├── websocket.py        # WebSocket handlers
├── static/
│   ├── index.html      # Main page
│   ├── style.css       # Styles
│   ├── app.js          # Frontend logic
│   └── highlight.min.js # Syntax highlighting
└── templates/
    └── index.html      # (альтернатива, если нужен Jinja2)
```

---

## 11. Зависимости

```python
# Добавить в requirements.txt
fastapi>=0.100.0
uvicorn>=0.23.0
websockets>=11.0.0
jinja2>=3.1.0
```

---

*Спецификация версия 1.0*  
*Дата: 2026-03-18*

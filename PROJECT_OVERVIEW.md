# ASTRA-M CodeSearch — Project Business Card

## 📌 Overview

**ASTRA-M CodeSearch** — интеллектуальная система поиска и анализа кода в репозиториях проекта ASTRA-M с использованием RAG (Retrieval-Augmented Generation). Предоставляет ответы на вопросы по коду через Telegram-бота и веб-интерфейс.

---

## 🎯 Цель

Закрытый инструмент для команды разработки, позволяющий быстро находить информацию по кодовой базе, архитектурам и реализациям в 5 репозиториях проекта.

---

## 👥 Целевая аудитория

- Разработчики команды ASTRA-M (backend, frontend, SE)
- Технические лиды и архитекторы
- Новые члены команды (onboarding)

---

## 🏗 Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                     ASTRA-M CodeSearch System                       │
│                                                                 │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │  Telegram   │    │   Web Browser   │    │  Docker Host    │  │
│  │     Bot     │    │   (Web UI)      │    │                 │  │
│  │  (polling)  │    │  (HTML + WS)    │    │  ┌───────────┐  │  │
│  └──────┬──────┘    └────────┬────────┘    │  │  Container│  │  │
│         │                    │              │  │           │  │  │
│         └────────────────────┼──────────────┼──┤  FastAPI  │  │
│                              │              │  │  + Bot    │  │
│                              │              │  │           │  │
│                    ┌─────────▼─────────┐    │  │  ┌─────┐  │  │
│                    │  RAG Pipeline     │    │  │  │Dict │  │  │
│                    │  - Retriever      │    │  │  │State│  │  │
│                    │  - Generator      │    │  │  └─────┘  │  │
│                    │  - Embeddings     │    │  └───────────┘  │
│                    └─────────┬─────────┘    │        │        │
│                              │              │        ▼        │
│                    ┌─────────▼─────────┐    │  ┌───────────┐  │
│                    │    Qdrant Cloud   │◄───┼──┤ /repos    │  │
│                    │  (qdrant.gotskin) │    │  │ (volume)  │  │
│                    └───────────────────┘    │  └───────────┘  │
│                                             └─────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Технологический стек

| Компонент | Технология | Версия |
|-----------|------------|--------|
| **Bot Framework** | python-telegram-bot | v20+ |
| **Web Framework** | FastAPI | v0.100+ |
| **Web Server** | uvicorn | v0.23+ |
| **Vector DB** | Qdrant | Remote (qdrant.gotskin.ru) |
| **Embeddings** | openai/text-embedding-3-small | OpenRouter |
| **LLM** | GLM-4 (Two-Agent), Gemini и др. (`.env`) | OpenRouter |
| **Chunking** | treesitter-chunker | v2.0+ |
| **Real-time** | WebSocket | Native |
| **Containerization** | Docker + docker-compose | — |
| **Language** | Python | 3.11 |

---

## 📦 Репозитории для индексации

| Репозиторий | Язык | Назначение |
|-------------|------|------------|
| backend | Java/Spring Boot | Бэкенд API |
| frontend | React/Vite | Веб-интерфейс |
| se | TypeScript | WYSIWYG редактор |
| landing | HTML/JS | Лендинг |
| pdf-2 | Python/JS | PDF сервис |

---

## 🚀 Функциональность

### Telegram Bot
| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/list` | Список репозиториев |
| `/add <repo>` | Добавить + индексация |
| `/remove <repo>` | Удалить репозиторий |
| `/reindex <repo>` | Переиндексировать |
| `/status` | Статус коллекций |
| `/mode` | Two-Agent / Simple (до рестарта) |
| `/adduser`, `/removeuser`, `/listusers`, `/id` | Whitelist |
| `<текст>` | RAG-запрос по коду |

### Web Interface
| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/` | GET | Веб-интерфейс (чат + управление) |
| `/api/query` | POST | RAG-запрос (SSE) |
| `/api/repos` | GET | Список репозиториев |
| `/api/repos/candidates` | GET | Кандидаты папок под `REPOS_BASE_PATH` |
| `/api/repos` | POST | Добавить репозиторий |
| `/api/repos/{name}` | DELETE | Удалить репозиторий |
| `/api/repos/{name}/reindex` | POST | Переиндексировать |
| `/api/repos/{name}/describe` | POST | Описание репо (LLM) |
| `/api/status` | GET | Статус системы |
| `/api/config` | GET | Runtime-настройки (модель, top_k, rag_mode) |
| `/api/config/runtime` | PUT | Обновить runtime-настройки |
| `/api/config/system` | GET | Системные параметры (маскированные секреты) |
| `/api/health` | GET | Health check |
| `/ws/state` | WebSocket | Real-time обновления статуса |

---

## 🔐 Безопасность

- **Whitelist пользователей** — только разрешённые Telegram-аккаунты
- **API Key защита** —.env переменные, не коммитятся в git
- **Изоляция** — Docker-контейнер без root-прав
- **Qdrant Auth** — API key для доступа к векторной БД

---

## 🏃 Запуск

### Локально (разработка)
```bash
pip install -r requirements.txt
cp .env.example .env
# Заполнить .env
python main.py
```

### Docker (production)
```bash
docker-compose up -d
# Доступ: http://localhost:8000
```

---

## 📊 RAG Pipeline

```
1. Chunking → Tree-sitter (семантические границы) + fallback (построчно)
2. Embeddings → openai/text-embedding-3-small (1536 dim)
3. Storage → Qdrant (отдельная коллекция на репозиторий)
4. Retrieval → Vector search (top_k из конфига RAG_SEARCH_TOP_K / лимиты в UI)
5. Generation → Two-Agent (GLM-4) или simple/agent ветка (OpenRouter)
```

---

## 📈 Мониторинг и логи

- **Logs** — stdout/stderr (JSON format)
- **State** — in-memory dict (индексация, прогресс)
- **Health check** — `/api/health` endpoint

---

## 🔮 Roadmap (потенциальные улучшения)

| Приоритет | Функция | Сложность |
|-----------|---------|-----------|
| 🔴 High | Redis для shared state (масштабирование) | Низкая |
| 🟡 Medium | История запросов и аналитика | Средняя |
| 🟢 Low | Мульти-бот (несколько Telegram-чатов) | Высокая |
| 🟢 Low | OAuth2 для Web UI | Средняя |

---

## 📞 Контакты

- **Репозиторий:** `astra-m-codesearch`
- **Владелец:** [Team Lead]
- **Документация:** `/README.md`, `/AGENTS.md`

---

*Версия: 2.0 (Docker + Web UI)*  
*Последнее обновление: Март 2026*

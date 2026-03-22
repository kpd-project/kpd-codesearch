# KPD CodeSearch — Project Business Card

## 📌 Overview

**KPD CodeSearch** — интеллектуальная система поиска и анализа кода в репозиториях KPD-проекта с использованием RAG (Retrieval-Augmented Generation). Предоставляет ответы на вопросы по коду через Telegram-бота и веб-интерфейс.

---

## 🎯 Цель

Закрытый инструмент для команды разработки, позволяющий быстро находить информацию по кодовой базе, архитектурам и реализациям в 5 репозиториях проекта.

---

## 👥 Целевая аудитория

- Разработчики KPD-команды (backend, frontend, SE)
- Технические лиды и архитекторы
- Новые члены команды (onboarding)

---

## 🏗 Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                     KPD CodeSearch System                       │
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
| **Embeddings** | text-embedding-3-small | OpenRouter |
| **LLM** | GLM-4 / Gemini 2.0 | OpenRouter |
| **Chunking** | treesitter-chunker | v2.0+ |
| **Real-time** | WebSocket | Native |
| **Containerization** | Docker + docker-compose | — |
| **Language** | Python | 3.11 |

---

## 📦 Репозитории для индексации

| Репозиторий | Язык | Назначение |
|-------------|------|------------|
| kpd-backend | Java/Spring Boot | Бэкенд API |
| kpd-frontend | React/Vite | Веб-интерфейс |
| kpd-se | TypeScript | WYSIWYG редактор |
| kpd-landing | HTML/JS | Лендинг |
| kpd-pdf-2 | Python/JS | PDF сервис |

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
| `<текст>` | RAG-запрос по коду |

### Web Interface
| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/` | GET | Веб-интерфейс (чат + управление) |
| `/api/query` | POST | RAG-запрос |
| `/api/repos` | GET | Список репозиториев |
| `/api/repos/{name}` | POST | Добавить репозиторий |
| `/api/repos/{name}` | DELETE | Удалить репозиторий |
| `/api/repos/{name}/reindex` | POST | Переиндексировать |
| `/api/status` | GET | Статус системы |
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
1. Chunking → Tree-sitter (семантические границы) + fallback (postрочно)
2. Embeddings → text-embedding-3-small (1536 dim)
3. Storage → Qdrant (отдельная коллекция на репозиторий)
4. Retrieval → Vector search (top_k=5)
5. Generation → GLM-4 via OpenRouter
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

- **Репозиторий:** `kpd-codesearch`
- **Владелец:** [Team Lead]
- **Документация:** `/README.md`, `/AGENTS.md`

---

*Версия: 2.0 (Docker + Web UI)*  
*Последнее обновление: Март 2026*

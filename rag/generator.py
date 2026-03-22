import json
import logging
import requests
import httpx
import config
from .retriever import search_all_repos, search_in_repo, get_file_from_qdrant
from .qdrant_client import collection_exists, list_collections

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = config.AGENT_SYSTEM_PROMPT

# Инструменты, доступные агенту
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "semantic_search",
            "description": (
                "Поиск по проиндексированным репозиториям. "
                "Можно искать в конкретном репо или по всем сразу. "
                "Вызывай несколько раз с разными формулировками запроса для лучшего результата. "
                "Для широких вопросов используй top_k ближе к максимуму — вернётся больше релевантных сниппетов (код полный, без обрезки)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос — что именно ищем в коде",
                    },
                    "repo": {
                        "type": "string",
                        "description": (
                            "Идентификатор репозитория из списка проиндексированных "
                            "(см. list_indexed_repos). Если не указан — поиск по всем."
                        ),
                    },
                    "top_k": {
                        "type": "integer",
                        "description": f"Количество результатов (по умолчанию {config.RAG_SEARCH_TOP_K}, максимум {config.RAG_SEARCH_TOP_K_MAX})",
                        "default": config.RAG_SEARCH_TOP_K,
                    },
                    "min_score": {
                        "type": "number",
                        "description": (
                            f"Порог релевантности 0–1 (ниже — отбрасывать). 0 = брать всё. "
                            f"По умолчанию {config.RAG_MIN_SCORE}. Снизь при пустом поиске."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_indexed_repos",
            "description": "Показывает список проиндексированных репозиториев. Используй перед поиском если не знаешь что проиндексировано.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Прочитать полное содержимое конкретного файла. "
                "Используй ТОЛЬКО если точно знаешь путь к файлу (например, из результатов semantic_search). "
                "Не используй semantic_search для чтения файлов — это разные инструменты."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Название репозитория (из list_indexed_repos)",
                    },
                    "path": {
                        "type": "string",
                        "description": "Точный путь к файлу (например, src/draw/index.ts)",
                    },
                },
                "required": ["repo", "path"],
            },
        },
    },
]


def _execute_tool(name: str, args: dict, on_status=None) -> str:
    logger.debug("Tool call: %s(%s)", name, args)
    if name == "list_indexed_repos":
        if on_status:
            on_status("📋 Проверяю список проиндексированных репозиториев…")
        indexed = list_collections()
        if not indexed:
            return "Нет проиндексированных репозиториев. Используй /add <repo> для индексации."
        return f"Проиндексированы: {', '.join(indexed)}"

    if name == "semantic_search":
        query = args.get("query", "")
        repo = args.get("repo")
        top_k = min(int(args.get("top_k", config.RAG_SEARCH_TOP_K)), config.RAG_SEARCH_TOP_K_MAX)
        min_score_arg = args.get("min_score")
        try:
            min_score = max(0, min(1, float(min_score_arg))) if min_score_arg is not None else None
        except (TypeError, ValueError):
            min_score = None
        if on_status:
            target = f" → {repo}" if repo else " → все репо"
            on_status(f"🔍 «{query[:80]}{'…' if len(query) > 80 else ''}»{target}")

        if repo:
            results = search_in_repo(repo, query, top_k, min_score)
            for r in results:
                r["repo"] = repo
        else:
            results = search_all_repos(query, top_k, min_score)

        if not results:
            return f"По запросу «{query}» ничего не найдено."

        parts = []
        for r in results:
            score = r.get("score", 0)
            path = r.get("path", "")
            repo_name = r.get("repo", "")
            content = r.get("content", "")
            if config.RAG_CHUNK_DISPLAY_CHARS > 0:
                content = content[:config.RAG_CHUNK_DISPLAY_CHARS]
            typ = r.get("type", "")
            type_hint = f" [{typ}]" if typ else ""
            parts.append(f"[score={score:.2f}] {repo_name}: {path}{type_hint}\n{content}")

        return "\n\n---\n\n".join(parts)

    if name == "read_file":
        repo = args.get("repo", "").strip()
        path = args.get("path", "").strip()
        if not repo or not path:
            return "Ошибка: укажи repo и path."
        if on_status:
            on_status(f"📄 Читаю {path} из {repo}…")

        try:
            file_path = config.REPOS_BASE_PATH / repo / path.lstrip("/").replace("\\", "/")
            if file_path.exists() and file_path.is_file():
                content = file_path.read_text(encoding="utf-8")
                if len(content) > 15000:
                    content = content[:15000] + "\n...(обрезано, файл слишком большой)..."
                return f"Содержимое {path} (с диска):\n```\n{content}\n```"
        except Exception as e:
            logger.warning("Не удалось прочитать с диска %s/%s: %s", repo, path, e)

        try:
            qdrant_content = get_file_from_qdrant(repo, path)
            if qdrant_content:
                if len(qdrant_content) > 15000:
                    qdrant_content = qdrant_content[:15000] + "\n...(обрезано)..."
                return f"Содержимое {path} (восстановлено из Qdrant):\n```\n{qdrant_content}\n```"
        except Exception as e:
            logger.error("Ошибка чтения %s/%s из Qdrant: %s", repo, path, e)

        return f"Файл {path} не найден ни на диске, ни в векторной базе."

    return f"Неизвестный инструмент: {name}"


def generate_answer(question: str, history: list[dict] = None, repo_name: str = None, on_status=None) -> tuple[str, dict]:
    """Агентный цикл: LLM сам решает сколько раз и с какими запросами искать.

    Возвращает (answer, session_data) где session_data содержит tool_calls и meta.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    # Добавляем историю переписки
    if history:
        messages.extend(history)

    # Добавляем текущий вопрос
    messages.append({"role": "user", "content": question})

    # Если указан конкретный репо — подсказываем агенту
    if repo_name:
        messages[-1]["content"] = f"{question}\n\n(Ищи в репозитории: {repo_name})"

    max_iterations = config.RAG_AGENT_MAX_ITERATIONS
    tool_calls_log: list[dict] = []
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _add_usage(data: dict) -> None:
        u = data.get("usage") or {}
        for k in usage_total:
            usage_total[k] += u.get(k) or 0

    for iteration in range(max_iterations):
        try:
            logger.debug("LLM request iteration %d, messages=%d", iteration + 1, len(messages))
            response = requests.post(
                f"{config.OPENROUTER_API_URL.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.OPENROUTER_MODEL,
                    "messages": messages,
                    "tools": TOOLS,
                    "tool_choice": "auto",
                    "max_tokens": config.RAG_AGENT_MAX_TOKENS,
                    "temperature": config.RAG_AGENT_TEMPERATURE,
                },
                timeout=config.RAG_AGENT_TIMEOUT,
            )
        except requests.exceptions.Timeout as e:
            logger.error("LLM timeout after %ds: %s", config.RAG_AGENT_TIMEOUT, e)
            answer = f"Таймаут при запросе к LLM ({config.RAG_AGENT_TIMEOUT}с). Попробуй позже."
            return answer, _make_session_data(tool_calls_log, iteration + 1, usage_total)
        except Exception as e:
            logger.error("LLM network error: %s", e)
            answer = f"Ошибка сети: {e}"
            return answer, _make_session_data(tool_calls_log, iteration + 1, usage_total)

        if response.status_code != 200:
            answer = f"Ошибка API ({response.status_code}): {response.text}"
            return answer, _make_session_data(tool_calls_log, iteration + 1, usage_total)

        data = response.json()
        _add_usage(data)
        choice = data["choices"][0]
        msg = choice["message"]

        # Финальный ответ — нет вызовов инструментов
        if not msg.get("tool_calls"):
            answer = msg.get("content") or "Нет ответа"
            return answer, _make_session_data(tool_calls_log, iteration + 1, usage_total)

        # Добавляем ответ ассистента с tool_calls в историю
        messages.append(msg)

        # Выполняем все запрошенные вызовы
        for tool_call in msg["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            try:
                tool_args = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError:
                tool_args = {}

            tool_result = _execute_tool(tool_name, tool_args, on_status=on_status)

            tool_calls_log.append({
                "tool": tool_name,
                "args": tool_args,
                "result_preview": tool_result[:config.RAG_LOG_RESULT_PREVIEW_LEN] if tool_result else "",
                "result_len": len(tool_result),
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": tool_result,
            })

    # Если достигли лимита итераций — просим финальный ответ без инструментов
    messages.append({
        "role": "user",
        "content": "Подведи итог на основе найденной информации.",
    })
    try:
        response = requests.post(
            f"{config.OPENROUTER_API_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.OPENROUTER_MODEL,
                "messages": messages,
                "max_tokens": config.RAG_AGENT_FINAL_MAX_TOKENS,
                "temperature": config.RAG_AGENT_TEMPERATURE,
            },
            timeout=config.RAG_AGENT_TIMEOUT,
        )
        data = response.json()
        _add_usage(data)
        answer = data["choices"][0]["message"].get("content") or "Не удалось подвести итог по найденным данным."
        return answer, _make_session_data(tool_calls_log, max_iterations, usage_total)
    except Exception as e:
        answer = f"Ошибка финального ответа: {e}"
        return answer, _make_session_data(tool_calls_log, max_iterations, usage_total)


RAG_CONTEXT_SYSTEM = (
    "Ты помощник по коду. Отвечай кратко, опираясь только на предоставленный контекст. "
    "Ответ в Markdown."
)


async def generate_response(
    query: str,
    context_chunks: list[dict],
    model: str | None = None,
    temperature: float = 0.1,
):
    """Стриминг ответа LLM по контексту (для Web API)."""
    model = model or config.OPENROUTER_MODEL
    context = "\n\n---\n\n".join(
        f"[{c.get('repo', '')}:{c.get('path', '')}]\n{c.get('content', '')}"
        for c in context_chunks
    )
    prompt = f"Контекст из кода:\n\n{context}\n\n---\n\nВопрос: {query}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{config.OPENROUTER_API_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": RAG_CONTEXT_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                "stream": True,
                "temperature": temperature,
                "max_tokens": 4000,
            },
        ) as resp:
            if resp.status_code != 200:
                raise RuntimeError(f"OpenRouter error {resp.status_code}: {await resp.aread()}")
            async for line in resp.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    try:
                        data = json.loads(line[6:])
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        pass


def generate_simple_answer(
    question: str,
    *,
    repo_name: str | None = None,
    top_k: int = 10,
    max_chunks: int = 10,
    model: str | None = None,
    temperature: float = 0.1,
    on_status=None,
) -> tuple[str, dict]:
    """Синхронный простой RAG: один векторный поиск + один ответ LLM (без агента)."""
    from .retriever import search_all_repos, search_in_repo

    if on_status:
        on_status("🔍 Ищу фрагменты кода…")

    if repo_name:
        chunks = search_in_repo(repo_name, question, top_k)
        for c in chunks:
            c["repo"] = repo_name
    else:
        chunks = search_all_repos(question, top_k)

    chunks = chunks[:max_chunks]

    if not chunks:
        msg = (
            "По запросу ничего не найдено в индексе. "
            "Переформулируйте вопрос или проверьте, что репозитории проиндексированы."
        )
        meta = simple_session_metadata()
        meta["model_primary"] = model or config.OPENROUTER_MODEL
        return msg, meta

    if on_status:
        on_status("✍️ Формирую ответ…")

    mdl = model or config.OPENROUTER_MODEL
    context = "\n\n---\n\n".join(
        f"[{c.get('repo', '')}:{c.get('path', '')}]\n{c.get('content', '')}"
        for c in chunks
    )
    prompt = f"Контекст из кода:\n\n{context}\n\n---\n\nВопрос: {question}"

    try:
        response = requests.post(
            f"{config.OPENROUTER_API_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": mdl,
                "messages": [
                    {"role": "system", "content": RAG_CONTEXT_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "temperature": temperature,
                "max_tokens": 4000,
            },
            timeout=config.RAG_AGENT_TIMEOUT,
        )
    except requests.exceptions.Timeout:
        answer = f"Таймаут при запросе к LLM ({config.RAG_AGENT_TIMEOUT}с)."
        meta = simple_session_metadata()
        meta["model_primary"] = mdl
        return answer, meta
    except Exception as e:
        answer = f"Ошибка: {e}"
        meta = simple_session_metadata()
        meta["model_primary"] = mdl
        return answer, meta

    if response.status_code != 200:
        answer = f"Ошибка API ({response.status_code}): {response.text[:500]}"
        meta = simple_session_metadata()
        meta["model_primary"] = mdl
        return answer, meta

    data = response.json()
    usage = data.get("usage") or {}
    answer = data["choices"][0]["message"].get("content") or "Нет ответа"
    meta = simple_session_metadata(usage)
    meta["model_primary"] = mdl
    return answer, meta


def _make_session_data(
    tool_calls_log: list[dict],
    iterations: int,
    usage: dict | None = None,
    *,
    simple: bool = False,
) -> dict:
    """Метаданные для лога: в умном режиме — две модели (цикл агента + финальный проход);
    в простом — только model_primary, model_secondary не пишем."""
    data: dict = {
        "model_primary": config.OPENROUTER_MODEL,
        "iterations": iterations,
        "tool_calls": tool_calls_log,
    }
    if not simple:
        data["model_secondary"] = config.OPENROUTER_MODEL
    if usage:
        data["usage"] = usage
    return data


def simple_session_metadata(usage: dict | None = None) -> dict:
    """Лог для простого RAG: один поиск чанков + один стриминговый ответ (без model_secondary)."""
    return _make_session_data([], 1, usage, simple=True)

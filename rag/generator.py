import json
import logging
import requests
import httpx
import config
from .retriever import search_all_repos, search_in_repo
from .qdrant_client import collection_exists, list_collections

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = config.AGENT_SYSTEM_PROMPT

# Инструменты, доступные агенту
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": (
                "Поиск по проиндексированным репозиториям KPD. "
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
                            "Имя репозитория для поиска (kpd-backend, kpd-frontend, kpd-se, "
                            "kpd-landing, kpd-pdf-2). Если не указан — ищет по всем."
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
]


def _execute_tool(name: str, args: dict, on_status=None) -> str:
    logger.debug("Tool call: %s(%s)", name, args)
    if name == "list_indexed_repos":
        indexed = list_collections()
        if not indexed:
            return "Нет проиндексированных репозиториев. Используй /add <repo> для индексации."
        return f"Проиндексированы: {', '.join(indexed)}"

    if name == "search_code":
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
    "Ты помощник по коду KPD-проекта. Отвечай кратко, опираясь только на предоставленный контекст."
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


def _make_session_data(tool_calls_log: list[dict], iterations: int, usage: dict | None = None) -> dict:
    data = {
        "model": config.OPENROUTER_MODEL,
        "iterations": iterations,
        "tool_calls": tool_calls_log,
    }
    if usage:
        data["usage"] = usage
    return data

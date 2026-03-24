"""Агент Describer: semantic_search + read_file → JSON для метаданных репозитория."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable

import requests

import config
from rag.agent.llm_client import parse_json_response
from rag.agent.schemas import DescriberResponse
from rag.generator import TOOLS, _execute_tool
from rag.qdrant_client import set_collection_properties

logger = logging.getLogger(__name__)

DESCRIBER_PROMPT = (Path(__file__).parent.parent / "prompts" / "describer.txt").read_text(encoding="utf-8").strip()

DESCRIBER_TOOLS = [t for t in TOOLS if t.get("function", {}).get("name") in frozenset({"semantic_search", "read_file"})]


def _add_usage(usage_total: dict, data: dict) -> None:
    u = data.get("usage") or {}
    for k in usage_total:
        usage_total[k] += u.get(k) or 0


def _describer_from_parsed(parsed: dict | None, repo_name: str) -> DescriberResponse | None:
    if not parsed:
        return None
    try:
        return DescriberResponse(
            suggested_name=(parsed.get("suggested_name") or "").strip() or repo_name,
            short_description=(parsed.get("short_description") or "").strip(),
            full_description=(parsed.get("full_description") or "").strip(),
        )
    except Exception as e:
        logger.warning("DescriberResponse build failed: %s", e)
        return None


def _finalize_json_only(
    messages: list[dict],
    usage_total: dict,
    *,
    repo_name: str,
    model: str,
    timeout: int,
) -> DescriberResponse | None:
    """Один запрос с json_object без инструментов — добить валидный JSON."""
    try:
        response = requests.post(
            f"{config.OPENAI_BASE_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages
                + [
                    {
                        "role": "user",
                        "content": (
                            "Верни единственный ответ — валидный JSON с полями "
                            "suggested_name, short_description, full_description. Без markdown."
                        ),
                    }
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": config.DESCRIBER_FINAL_MAX_TOKENS,
                "temperature": 0.1,
            },
            timeout=timeout,
            verify=False,
        )
    except Exception as e:
        logger.error("Describer finalize JSON request failed: %s", e)
        return None

    if response.status_code != 200:
        logger.error("Describer finalize JSON API error: %s %s", response.status_code, response.text[:500])
        return None

    data = response.json()
    _add_usage(usage_total, data)
    content = data["choices"][0]["message"].get("content") or ""
    parsed = parse_json_response(content)
    return _describer_from_parsed(parsed, repo_name)


def run_describer_agent(
    repo_name: str,
    on_status: Callable[[str], None] | None = None,
) -> tuple[DescriberResponse, dict]:
    """Синхронный цикл агента с инструментами; итог — DescriberResponse и usage/tool_calls."""
    messages: list[dict] = [
        {"role": "system", "content": DESCRIBER_PROMPT},
        {
            "role": "user",
            "content": (
                f"Репозиторий для анализа: `{repo_name}`.\n"
                f"В semantic_search всегда передавай \"repo\": \"{repo_name}\" "
                f"(поиск только по этой коллекции).\n"
                f"В read_file указывай \"repo\": \"{repo_name}\" и path из результатов поиска.\n"
                "Когда соберёшь достаточно контекста — ответь одним сообщением: только JSON "
                "с полями suggested_name, short_description, full_description, без вызова инструментов."
            ),
        },
    ]

    usage_total: dict = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    tool_calls_log: list[dict] = []
    model = config.DESCRIBER_MODEL
    max_iterations = config.DESCRIBER_MAX_ITERATIONS
    timeout = config.DESCRIBER_TIMEOUT

    for iteration in range(max_iterations):
        try:
            response = requests.post(
                f"{config.OPENAI_BASE_URL.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "tools": DESCRIBER_TOOLS,
                    "tool_choice": "auto",
                    "max_tokens": config.DESCRIBER_MAX_TOKENS,
                    "temperature": config.DESCRIBER_TEMPERATURE,
                },
                timeout=timeout,
                verify=False,
            )
        except requests.exceptions.Timeout:
            logger.error("Describer LLM timeout after %ds", timeout)
            break
        except Exception as e:
            logger.error("Describer LLM error: %s", e)
            break

        if response.status_code != 200:
            logger.error("Describer API error (%s): %s", response.status_code, response.text[:500])
            break

        data = response.json()
        _add_usage(usage_total, data)
        msg = data["choices"][0]["message"]

        if not msg.get("tool_calls"):
            content = msg.get("content") or ""
            parsed = parse_json_response(content)
            result = _describer_from_parsed(parsed, repo_name)
            if result and result.short_description and result.full_description:
                return result, _session_data(tool_calls_log, usage_total, iteration + 1)
            if result and (result.short_description or result.full_description):
                messages.append(msg)
                break
            if content.strip():
                logger.warning("Describer: не JSON, пробуем финальный json_object")
            messages.append(msg)
            break

        messages.append(msg)

        for tool_call in msg["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            try:
                tool_args = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError:
                tool_args = {}

            tool_result = _execute_tool(tool_name, tool_args, on_status=on_status)

            tool_calls_log.append(
                {
                    "tool": tool_name,
                    "args": tool_args,
                    "result_preview": tool_result[: config.RAG_LOG_RESULT_PREVIEW_LEN] if tool_result else "",
                    "result_len": len(tool_result),
                }
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": tool_result,
                }
            )

    finalized = _finalize_json_only(
        messages, usage_total, repo_name=repo_name, model=model, timeout=timeout
    )
    if finalized and (finalized.short_description.strip() or finalized.full_description.strip()):
        return finalized, _session_data(tool_calls_log, usage_total, max_iterations + 1)

    return (
        DescriberResponse(
            suggested_name=repo_name,
            short_description="",
            full_description="",
        ),
        _session_data(tool_calls_log, usage_total, max_iterations + 1),
    )


def apply_describer_metadata(repo_name: str, result: DescriberResponse) -> bool:
    """Сливает suggested_name, short_description, full_description в коллекцию; полное дублирует в description."""
    if not result.short_description.strip() and not result.full_description.strip():
        return False
    payload: dict = {
        "suggested_name": (result.suggested_name.strip() or repo_name),
    }
    if result.short_description.strip():
        payload["short_description"] = result.short_description.strip()
    if result.full_description.strip():
        fd = result.full_description.strip()
        payload["full_description"] = fd
        payload["description"] = fd
    return set_collection_properties(repo_name, payload)


def _session_data(tool_calls_log: list[dict], usage: dict, iterations: int) -> dict:
    return {
        "model_primary": config.DESCRIBER_MODEL,
        "iterations": iterations,
        "tool_calls": tool_calls_log,
        "usage": usage,
    }

import logging
from pathlib import Path

import config
from .llm_client import LLMClient, parse_json_response
from .schemas import AnswererResponse, SummarizedContext

logger = logging.getLogger(__name__)

ANSWERER_PROMPT = (Path(__file__).parent.parent.parent / "prompts" / "answerer.txt").read_text(encoding="utf-8").strip()

def _build_context_text(summarized_context: SummarizedContext, question: str) -> str:
    """Собирает контекст из саммари для передачи Answerer'у."""
    parts: list[str] = [
        f"Вопрос пользователя: {question}",
        "",
        "Сводка по найденному коду:",
        summarized_context.summary,
        "",
        "Ключевые цитаты:"
    ]

    for i, citation in enumerate(summarized_context.citations, 1):
        parts.append(f"[{i}] {citation}")

    parts.extend([
        "",
        "Затронутые файлы:",
        ", ".join(summarized_context.files_involved)
    ])

    return "\n".join(parts)


class AnswererAgent:
    def __init__(self):
        self.model = config.ANSWERER_MODEL
        self.temperature = config.ANSWERER_TEMPERATURE
        self.max_tokens = config.ANSWERER_MAX_TOKENS
        self.max_reasoning_tokens = config.ANSWERER_MAX_REASONING_TOKENS
        self.timeout = config.ANSWERER_TIMEOUT
        self._client = LLMClient()

    async def answer(
        self,
        question: str,
        summarized_context: SummarizedContext,
        history: list[dict] | None = None,
        iteration: int = 1,
    ) -> tuple[AnswererResponse, dict]:
        messages = [{"role": "system", "content": ANSWERER_PROMPT}]

        if history:
            messages.extend(history[-config.ANSWERER_HISTORY_LIMIT:])

        context_text = _build_context_text(summarized_context, question)
        messages.append({"role": "user", "content": context_text})

        if iteration > 1:
            messages.append({
                "role": "user",
                "content": (
                    f"Это попытка #{iteration}. "
                    "Пожалуйста, либо дай ответ на основе найденных фрагментов, "
                    "либо запроси дополнительный поиск с уточнёнными запросами."
                ),
            })

        # Ограничиваем "раздумья" для think-моделей (o3-mini, claude-3.7-sonnet и др.)
        # через параметр max_completion_tokens (OpenAI-compatible API; COT + итоговый ответ).
        extra_payload: dict | None = None
        if self.max_reasoning_tokens > 0:
            extra_payload = {"max_completion_tokens": self.max_tokens + self.max_reasoning_tokens}

        content, usage = await self._client.chat(
            messages=messages,
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            timeout=self.timeout,
            json_mode=True,
            extra_payload=extra_payload,
        )

        parsed = parse_json_response(content)
        if parsed is not None:
            try:
                answerer_response = AnswererResponse(**parsed)
            except Exception as e:
                logger.error("Failed to build AnswererResponse: %s\nParsed: %s", e, parsed)
                answerer_response = AnswererResponse(
                    answer="Не удалось сформировать ответ. Попробуйте переформулировать вопрос.",
                    need_more=False,
                )
        else:
            logger.error("Failed to parse Answerer response\nContent: %s...", content[:200])
            if len(content) > 50 and "{" not in content:
                answerer_response = AnswererResponse(answer=content, need_more=False)
            else:
                answerer_response = AnswererResponse(
                    answer="Не удалось сформировать ответ. Попробуйте переформулировать вопрос.",
                    need_more=False,
                )

        return answerer_response, {"tokens": usage}

    def needs_more_search(self, response: AnswererResponse) -> bool:
        return response.need_more and response.queries is not None and len(response.queries) > 0

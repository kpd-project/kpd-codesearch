import json
import logging
import requests
from pathlib import Path

import config
from .schemas import AnswererResponse, SearchQuery, SummarizedContext

logger = logging.getLogger(__name__)

ANSWERER_PROMPT = (Path(__file__).parent.parent.parent / "prompts" / "answerer.txt").read_text(encoding="utf-8").strip()


class AnswererAgent:
    def __init__(self):
        self.model = config.ANSWERER_MODEL
        self.temperature = config.ANSWERER_TEMPERATURE
        self.max_tokens = config.ANSWERER_MAX_TOKENS
        self.timeout = config.ANSWERER_TIMEOUT

    def answer(
        self,
        question: str,
        summarized_context: SummarizedContext,
        history: list[dict] | None = None,
        iteration: int = 1,
    ) -> tuple[AnswererResponse, dict]:
        messages = [{"role": "system", "content": ANSWERER_PROMPT}]
        
        if history:
            for msg in history[-config.ANSWERER_HISTORY_LIMIT:]:
                messages.append(msg)
        
        context_text = f"""Вопрос пользователя: {question}

Найденный контекст:
{summarized_context.summary}

Затронутые файлы: {', '.join(summarized_context.files_involved)}

Уверенность в релевантности: {summarized_context.confidence:.0%}

Ключевые фрагменты:
""" + "\n".join(f"- {c}" for c in summarized_context.citations[:5]) if summarized_context.citations else ""

        messages.append({"role": "user", "content": context_text})
        
        if iteration > 1:
            messages.append({
                "role": "user",
                "content": f"Это попытка #{iteration}. Пожалуйста, либо дай ответ, либо запроси дополнительный поиск с уточнёнными запросами."
            })
        
        response = requests.post(
            f"{config.OPENROUTER_API_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            },
            timeout=self.timeout,
        )
        
        if response.status_code != 200:
            raise Exception(f"Answerer API error ({response.status_code}): {response.text}")
        
        data = response.json()
        content = data["choices"][0]["message"].get("content", "")
        usage = data.get("usage", {})
        
        def _try_parse(raw: str) -> AnswererResponse | None:
            for candidate in [raw.strip(), raw]:
                try:
                    parsed = json.loads(candidate)
                    return AnswererResponse(**parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
            # Извлечь JSON-объект из текста вида "json\n{...}" или markdown-блока
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    parsed = json.loads(raw[start:end])
                    return AnswererResponse(**parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
            return None

        answerer_response = _try_parse(content)
        if answerer_response is None:
            logger.error(f"Failed to parse Answerer response\nContent: {content[:200]}...")
            if len(content) > 50 and "{" not in content:
                answerer_response = AnswererResponse(answer=content, need_more=False)
            else:
                answerer_response = AnswererResponse(
                    answer="Не удалось сформировать ответ. Попробуйте переформулировать вопрос.",
                    need_more=False
                )
        
        return answerer_response, {"tokens": usage}

    def needs_more_search(self, response: AnswererResponse) -> bool:
        return response.need_more and response.queries is not None and len(response.queries) > 0
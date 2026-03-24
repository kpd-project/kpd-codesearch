import json
import logging
import re

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

import config

logger = logging.getLogger(__name__)

_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


def _should_retry(exc: BaseException) -> bool:
    """Повторять только на сетевые ошибки и retryable HTTP-статусы."""
    if isinstance(exc, (httpx.NetworkError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in _RETRY_STATUS_CODES:
        return True
    return False


class LLMClient:
    """Единый async HTTP-клиент для OpenAI-compatible LLM API.

    Инкапсулирует заголовки авторизации, retry-логику (Exponential Backoff 1s→2s→4s)
    и базовую обработку ответа. Используется Analyst и Answerer агентами.
    """

    def __init__(self) -> None:
        self._base_url = config.OPENAI_BASE_URL.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception(_should_retry),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def chat(
        self,
        messages: list[dict],
        model: str,
        max_tokens: int,
        temperature: float,
        timeout: int,
        json_mode: bool = False,
        extra_payload: dict | None = None,
    ) -> tuple[str, dict]:
        """Отправить запрос к /chat/completions, вернуть (content, usage).

        При сетевых ошибках и статусах 429/5xx — до 3 попыток с Exponential Backoff.
        """
        payload: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if extra_payload:
            payload.update(extra_payload)

        async with httpx.AsyncClient(timeout=float(timeout), verify=False) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers,
                json=payload,
            )

        # raise_for_status на retryable-статусах → tenacity перехватит HTTPStatusError
        if response.status_code in _RETRY_STATUS_CODES:
            response.raise_for_status()

        if response.status_code != 200:
            raise Exception(f"LLM API error ({response.status_code}): {response.text}")

        data = response.json()
        content = data["choices"][0]["message"].get("content", "")
        usage = data.get("usage", {})
        return content, usage


def parse_json_response(content: str) -> dict | None:
    """Надёжный парсер JSON из ответа LLM.

    Попытки по убыванию надёжности:
    1. Прямой json.loads
    2. Извлечение из markdown-блока ```json...```
    3. Поиск первого {…} в тексте
    """
    try:
        return json.loads(content.strip())
    except (json.JSONDecodeError, TypeError):
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass

    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(content[start:end])
        except (json.JSONDecodeError, TypeError):
            pass

    return None

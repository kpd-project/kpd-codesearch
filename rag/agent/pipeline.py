import logging
from typing import Callable

import config
from .analyst import AnalystAgent
from .answerer import AnswererAgent
from .schemas import PipelineState, SearchQuery

logger = logging.getLogger(__name__)


def generate_answer_two_agent(
    question: str,
    history: list[dict] | None = None,
    on_status: Callable[[str], None] | None = None,
) -> tuple[str, dict]:
    analyst = AnalystAgent()
    answerer = AnswererAgent()

    state = PipelineState(original_question=question)
    hints: list[str] = []
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _add_usage(usage: dict, source: str):
        tokens = usage.get("tokens", {})
        for k in ["prompt_tokens", "completion_tokens", "total_tokens"]:
            val = tokens.get(k, 0) or 0
            total_usage[k] += val

    max_iterations = config.PIPELINE_MAX_ITERATIONS

    for iteration in range(1, max_iterations + 1):
        state.iteration = iteration

        if on_status:
            on_status(f"🤔 Анализирую запрос (итерация {iteration})...")

        try:
            analyst_response, analyst_usage = analyst.analyze(
                question=question,
                history=history,
                hints=hints if iteration > 1 else None,
            )
            state.analyst_response = analyst_response
            _add_usage(analyst_usage, "analyst")

            logger.debug(
                "Analyst iteration %d: queries=%d, confidence=%.2f",
                iteration, len(analyst_response.queries), analyst_response.confidence,
            )
        except Exception as e:
            logger.error("Analyst error: %s", e)
            return f"Ошибка анализа запроса: {e}", _make_session_data(state, total_usage)

        if on_status:
            queries_preview = ", ".join(q.text[:30] for q in analyst_response.queries[:3])
            on_status(f"🔍 Ищу: {queries_preview}...")

        try:
            search_results = analyst.search(analyst_response.queries, on_status=on_status)
            state.search_results = search_results

            logger.debug("Search iteration %d: found %d results", iteration, len(search_results))
        except Exception as e:
            logger.error("Search error: %s", e)
            return f"Ошибка поиска: {e}", _make_session_data(state, total_usage)

        if on_status:
            on_status(f"✍️ Формирую ответ ({len(search_results)} фрагментов кода)...")

        try:
            answerer_response, answerer_usage = answerer.answer(
                question=question,
                search_results=search_results,
                history=history,
                iteration=iteration,
            )
            state.answerer_response = answerer_response
            _add_usage(answerer_usage, "answerer")

            logger.debug(
                "Answerer iteration %d: need_more=%s, has_answer=%s",
                iteration, answerer_response.need_more, answerer_response.answer is not None,
            )
        except Exception as e:
            logger.error("Answerer error: %s", e)
            return f"Ошибка формирования ответа: {e}", _make_session_data(state, total_usage)

        if not answerer.needs_more_search(answerer_response):
            answer = answerer_response.answer or "Не удалось сформировать ответ."
            return answer, _make_session_data(state, total_usage)

        if iteration < max_iterations:
            if on_status:
                on_status(f"🔄 Уточняю поиск (итерация {iteration + 1})...")

            hints = answerer_response.hints or []

            new_queries = []
            for q in (answerer_response.queries or []):
                new_queries.append(SearchQuery(
                    text=q.text,
                    repo=q.repo,
                    top_k=q.top_k or config.RAG_SEARCH_TOP_K,
                    min_score=getattr(q, "min_score", None),
                ))

            # Подменяем запросы для следующей итерации поиска по уточнениям от Answerer
            if new_queries:
                state.analyst_response.queries = new_queries

            logger.info("Iteration %d: requesting more search with %d queries", iteration, len(new_queries))
        else:
            answer = answerer_response.answer or (
                "Не удалось найти достаточно информации для ответа. "
                "Попробуйте переформулировать вопрос."
            )
            return answer, _make_session_data(state, total_usage)

    return "Превышен лимит итераций. Попробуйте упростить вопрос.", _make_session_data(state, total_usage)


def _make_session_data(state: PipelineState, usage: dict) -> dict:
    return {
        "pipeline": "two_agent",
        "iterations": state.iteration,
        "analyst": {
            "queries": [{"text": q.text, "repo": q.repo} for q in state.analyst_response.queries],
            "analysis": state.analyst_response.analysis,
            "confidence": state.analyst_response.confidence,
        } if state.analyst_response else None,
        "search": {
            "results_count": len(state.search_results),
            "files": list(set(f"{r.repo}:{r.path}" for r in state.search_results)),
        } if state.search_results else None,
        "answerer": {
            "need_more": state.answerer_response.need_more if state.answerer_response else None,
            "hints": state.answerer_response.hints if state.answerer_response else None,
        } if state.answerer_response else None,
        "usage": usage,
    }
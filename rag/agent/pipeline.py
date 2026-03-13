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
            
            logger.debug(f"Analyst iteration {iteration}: queries={len(analyst_response.queries)}, confidence={analyst_response.confidence}")
        except Exception as e:
            logger.error(f"Analyst error: {e}")
            return f"Ошибка анализа запроса: {e}", _make_session_data(state, total_usage)
        
        if on_status:
            queries_preview = ", ".join(q.text[:30] for q in analyst_response.queries[:3])
            on_status(f"🔍 Ищу: {queries_preview}...")
        
        try:
            search_results = analyst.search(analyst_response.queries, on_status=on_status)
            state.search_results = search_results
            
            logger.debug(f"Search iteration {iteration}: found {len(search_results)} results")
        except Exception as e:
            logger.error(f"Search error: {e}")
            return f"Ошибка поиска: {e}", _make_session_data(state, total_usage)
        
        if on_status:
            on_status(f"📝 Анализирую найденное ({len(search_results)} результатов)...")
        
        try:
            summarized_context = analyst.summarize(search_results, question)
            state.summarized_context = summarized_context
            
            logger.debug(f"Summarized: files={len(summarized_context.files_involved)}, confidence={summarized_context.confidence}")
        except Exception as e:
            logger.error(f"Summarize error: {e}")
            summarized_context = state.summarized_context
        
        if on_status:
            on_status(f"✍️ Формирую ответ...")
        
        try:
            answerer_response, answerer_usage = answerer.answer(
                question=question,
                summarized_context=summarized_context,
                history=history,
                iteration=iteration,
            )
            state.answerer_response = answerer_response
            _add_usage(answerer_usage, "answerer")
            
            logger.debug(f"Answerer iteration {iteration}: need_more={answerer_response.need_more}, has_answer={answerer_response.answer is not None}")
        except Exception as e:
            logger.error(f"Answerer error: {e}")
            return f"Ошибка формирования ответа: {e}", _make_session_data(state, total_usage)
        
        if not answerer.needs_more_search(answerer_response):
            answer = answerer_response.answer or "Не удалось сформировать ответ."
            return answer, _make_session_data(state, total_usage)
        
        if iteration < max_iterations:
            if on_status:
                on_status(f"🔄 Уточняю поиск...")
            
            hints = answerer_response.hints or []
            hints.append(f"Текущая уверенность: {summarized_context.confidence:.0%}")
            
            new_queries = []
            for q in (answerer_response.queries or []):
                new_queries.append(SearchQuery(
                    text=q.text,
                    repo=q.repo,
                    top_k=q.top_k or config.RAG_SEARCH_TOP_K,
                    min_score=getattr(q, 'min_score', None),
                ))
            
            logger.info(f"Iteration {iteration}: requesting more search with {len(new_queries)} queries")
        else:
            answer = answerer_response.answer or "Не удалось найти достаточно информации для ответа. Попробуйте переформулировать вопрос."
            return answer, _make_session_data(state, total_usage)
    
    return "Превышен лимит итераций. Попробуйте упростить вопрос.", _make_session_data(state, total_usage)


def _make_session_data(state: PipelineState, usage: dict) -> dict:
    return {
        "pipeline": "two_agent",
        "iterations": state.iteration,
        "analyst": {
            "queries": [{"text": q.text, "repo": q.repo} for q in state.analyst_response.queries] if state.analyst_response else [],
            "analysis": state.analyst_response.analysis if state.analyst_response else None,
            "confidence": state.analyst_response.confidence if state.analyst_response else None,
        } if state.analyst_response else None,
        "search": {
            "results_count": len(state.search_results),
            "files": list(set(f"{r.repo}:{r.path}" for r in state.search_results)),
            "summarized_confidence": state.summarized_context.confidence if state.summarized_context else None,
        } if state.search_results else None,
        "answerer": {
            "need_more": state.answerer_response.need_more if state.answerer_response else None,
            "hints": state.answerer_response.hints if state.answerer_response else None,
        } if state.answerer_response else None,
        "usage": usage,
    }
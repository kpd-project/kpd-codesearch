import json
import logging
import requests
from pathlib import Path
from typing import Callable

import config
from .schemas import AnalystResponse, SearchQuery, SearchResult, SummarizedContext
from ..retriever import search_in_repo, search_all_repos

logger = logging.getLogger(__name__)

ANALYST_PROMPT = (Path(__file__).parent.parent.parent / "prompts" / "analyst.txt").read_text(encoding="utf-8").strip()


class AnalystAgent:
    def __init__(self):
        self.model = config.ANALYST_MODEL
        self.temperature = config.ANALYST_TEMPERATURE
        self.max_tokens = config.ANALYST_MAX_TOKENS
        self.timeout = config.ANALYST_TIMEOUT

    def analyze(self, question: str, history: list[dict] | None = None, hints: list[str] | None = None) -> tuple[AnalystResponse, dict]:
        messages = [{"role": "system", "content": ANALYST_PROMPT}]
        
        if history:
            for msg in history[-config.ANALYST_HISTORY_LIMIT:]:
                messages.append(msg)
        
        user_content = question
        if hints:
            user_content += f"\n\nПодсказки от предыдущего поиска:\n" + "\n".join(f"- {h}" for h in hints)
        
        messages.append({"role": "user", "content": user_content})
        
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
            raise Exception(f"Analyst API error ({response.status_code}): {response.text}")
        
        data = response.json()
        content = data["choices"][0]["message"].get("content", "")
        usage = data.get("usage", {})
        
        try:
            parsed = json.loads(content)
            analyst_response = AnalystResponse(**parsed)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse Analyst response: {e}\nContent: {content}")
            analyst_response = AnalystResponse(
                queries=[SearchQuery(text=question)],
                analysis=f"Не удалось разобрать ответ: {e}",
                confidence=0.3
            )
        
        return analyst_response, {"tokens": usage}

    def search(self, queries: list[SearchQuery], on_status: Callable[[str], None] | None = None) -> list[SearchResult]:
        all_results = []
        
        for query in queries:
            if on_status:
                target = f" → {query.repo}" if query.repo else " → все репо"
                on_status(f"🔍 «{query.text[:60]}{'…' if len(query.text) > 60 else ''}»{target}")
            
            top_k = query.top_k or config.RAG_SEARCH_TOP_K
            top_k = min(top_k, config.RAG_SEARCH_TOP_K_MAX)
            min_score = query.min_score
            
            if query.repo:
                results = search_in_repo(query.repo, query.text, top_k, min_score)
                for r in results:
                    r["repo"] = query.repo
            else:
                results = search_all_repos(query.text, top_k, min_score)
            
            for r in results:
                all_results.append(SearchResult(
                    content=r.get("content", ""),
                    path=r.get("path", ""),
                    repo=r.get("repo", ""),
                    language=r.get("language", ""),
                    type=r.get("type", ""),
                    score=r.get("score", 0.0),
                ))
        
        unique_results = {}
        for r in all_results:
            key = f"{r.repo}:{r.path}:{r.content[:100]}"
            if key not in unique_results or r.score > unique_results[key].score:
                unique_results[key] = r
        
        return sorted(unique_results.values(), key=lambda x: x.score, reverse=True)

    def summarize(self, results: list[SearchResult], question: str) -> SummarizedContext:
        if not results:
            return SummarizedContext(
                summary="Ничего не найдено.",
                citations=[],
                files_involved=[],
                confidence=0.0
            )
        
        context_parts = []
        files = set()
        
        for i, r in enumerate(results[:15], 1):
            content = r.content
            if config.RAG_CHUNK_DISPLAY_CHARS > 0:
                content = content[:config.RAG_CHUNK_DISPLAY_CHARS]
            
            type_hint = f" [{r.type}]" if r.type else ""
            context_parts.append(f"[{i}] {r.repo}: {r.path}{type_hint} (score={r.score:.2f})\n{content}")
            files.add(f"{r.repo}:{r.path}")
        
        context_text = "\n\n---\n\n".join(context_parts)
        
        summarize_prompt = f"""Проанализируй найденный контекст и подготовь сжатую сводку для ответа пользователю.

Вопрос: {question}

Найденный контекст:
{context_text}

Выведи JSON:
{{
  "summary": "сжатое описание что найдено и как это отвечает на вопрос",
  "citations": ["ключевая цитата 1", "ключевая цитата 2"],
  "confidence": 0.8
}}

Важно: только валидный JSON, без markdown."""

        response = requests.post(
            f"{config.OPENROUTER_API_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": summarize_prompt}],
                "max_tokens": config.ANALYST_MAX_TOKENS,
                "temperature": 0.3,
            },
            timeout=self.timeout,
        )
        
        if response.status_code != 200:
            logger.error(f"Summarize API error: {response.status_code}")
            return SummarizedContext(
                summary=f"Найдено {len(results)} результатов",
                citations=[r.content[:200] for r in results[:3]],
                files_involved=list(files),
                confidence=0.5
            )
        
        content = response.json()["choices"][0]["message"].get("content", "")
        
        try:
            parsed = json.loads(content)
            return SummarizedContext(
                summary=parsed.get("summary", ""),
                citations=parsed.get("citations", []),
                files_involved=list(files),
                confidence=parsed.get("confidence", 0.7),
            )
        except json.JSONDecodeError:
            return SummarizedContext(
                summary=content[:500],
                citations=[r.content[:200] for r in results[:3]],
                files_involved=list(files),
                confidence=0.5
            )
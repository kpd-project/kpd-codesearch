import json
import logging
import requests
from pathlib import Path
from typing import Callable

import config
from .schemas import AnalystResponse, SearchQuery, SearchResult
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

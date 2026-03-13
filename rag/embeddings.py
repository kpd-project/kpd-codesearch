"""Эмбеддинги через OpenRouter API. Прямой вызов без LangChain — без tiktoken и зависаний."""

from openai import OpenAI

import config

EMBEDDINGS = None


def get_embeddings():
    """Совместимый с LangChain объект: embed_query(s) и embed_documents(texts)."""
    global EMBEDDINGS
    if EMBEDDINGS is None:
        model = config.EMBEDDINGS_MODEL
        if model == "text-embedding-3-small":
            model = "openai/text-embedding-3-small"
        client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_API_URL.rstrip("/"),
        )

        class OpenRouterEmbeddings:
            def embed_query(self, text: str) -> list[float]:
                r = client.embeddings.create(model=model, input=text)
                return r.data[0].embedding

            def embed_documents(self, texts: list[str]) -> list[list[float]]:
                if not texts:
                    return []
                r = client.embeddings.create(model=model, input=texts)
                return [d.embedding for d in sorted(r.data, key=lambda x: x.index)]

        EMBEDDINGS = OpenRouterEmbeddings()
    return EMBEDDINGS

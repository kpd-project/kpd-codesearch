"""Эмбеддинги через OpenRouter API. Прямой вызов без LangChain — без tiktoken и зависаний."""

import asyncio
import logging
from openai import OpenAI, AsyncOpenAI
import httpx

import config

logger = logging.getLogger(__name__)

EMBEDDINGS = None
ASYNC_EMBEDDINGS = None


def get_embeddings():
    """Синхронный интерфейс: embed_query(s) и embed_documents(texts).
    
    Использует синхронный OpenAI клиент — безопасно для вызова из executor'а.
    """
    global EMBEDDINGS
    if EMBEDDINGS is None:
        model = config.EMBEDDINGS_MODEL
        if model == "text-embedding-3-small":
            model = "openai/text-embedding-3-small"

        # Создаём один синхронный клиент — не требует event loop
        client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_API_URL.rstrip("/"),
            timeout=httpx.Timeout(config.EMBED_REQUEST_TIMEOUT),
        )

        class OpenRouterEmbeddings:
            def embed_query(self, text: str):
                logger.debug("embed_query: len=%d", len(text))
                try:
                    r = client.embeddings.create(model=model, input=text)
                    logger.debug("embed_query: done")
                    return r.data[0].embedding
                except Exception as e:
                    logger.error("embed_query failed: %s", e)
                    raise

            def embed_documents(self, texts: list[str]):
                if not texts:
                    return []
                logger.debug("embed_documents: count=%d", len(texts))
                try:
                    r = client.embeddings.create(model=model, input=texts)
                    logger.debug("embed_documents: done")
                    return [d.embedding for d in sorted(r.data, key=lambda x: x.index)]
                except Exception as e:
                    logger.error("embed_documents failed: %s", e)
                    raise

        EMBEDDINGS = OpenRouterEmbeddings()
    return EMBEDDINGS


def get_async_embeddings():
    """Асинхронный интерфейс: embed_query_async() и embed_documents_async()."""
    global ASYNC_EMBEDDINGS
    if ASYNC_EMBEDDINGS is None:
        model = config.EMBEDDINGS_MODEL
        if model == "text-embedding-3-small":
            model = "openai/text-embedding-3-small"

        class AsyncOpenRouterEmbeddings:
            def __init__(self):
                self._client = None
                self._semaphore = asyncio.Semaphore(config.EMBED_MAX_CONCURRENT)

            @property
            def client(self):
                if self._client is None:
                    self._client = AsyncOpenAI(
                        api_key=config.OPENROUTER_API_KEY,
                        base_url=config.OPENROUTER_API_URL.rstrip("/"),
                        timeout=httpx.Timeout(config.EMBED_REQUEST_TIMEOUT),
                    )
                return self._client

            async def embed_query_async(self, text: str):
                async with self._semaphore:
                    r = await self.client.embeddings.create(model=model, input=text)
                    return r.data[0].embedding

            async def embed_documents_async(self, texts: list[str]):
                if not texts:
                    return []

                async def embed_batch(batch: list[str]):
                    async with self._semaphore:
                        r = await self.client.embeddings.create(model=model, input=batch)
                        return [d.embedding for d in sorted(r.data, key=lambda x: x.index)]

                results = await embed_batch(texts)
                return results

        ASYNC_EMBEDDINGS = AsyncOpenRouterEmbeddings()
    return ASYNC_EMBEDDINGS

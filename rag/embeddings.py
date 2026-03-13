import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain")

from langchain_community.embeddings import OpenAIEmbeddings
import config

EMBEDDINGS = None

def get_embeddings():
    global EMBEDDINGS
    if EMBEDDINGS is None:
        EMBEDDINGS = OpenAIEmbeddings(
            model=config.EMBEDDINGS_MODEL,
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=config.OPENROUTER_API_KEY,
            # dimensions не передаём — OpenRouter его игнорирует/отклоняет,
            # text-embedding-3-small возвращает 1536 по умолчанию
        )
    return EMBEDDINGS

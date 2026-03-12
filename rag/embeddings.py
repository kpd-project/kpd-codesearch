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
            dimensions=config.EMBEDDINGS_DIMENSION,  # Qwen3-8B: 4096 по умолч., или меньше (Matryoshka)
        )
    return EMBEDDINGS

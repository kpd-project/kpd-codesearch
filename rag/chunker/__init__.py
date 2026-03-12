"""
Семантический чанкинг кода: Tree-sitter для Java, JS, TS, Python и др., fallback — построчно.
"""

from pathlib import Path
import config

from .base import iter_code_files, get_language
from .semantic import chunk_file as semantic_chunk
from .fallback import chunk_file as fallback_chunk


def chunk_file(path: Path, repo_name: str, base_path: Path) -> list[dict]:
    """Сначала семантика (Tree-sitter), при пустом или ошибке — построчно."""
    chunks = semantic_chunk(path, repo_name, base_path)
    if not chunks:
        chunks = fallback_chunk(path, repo_name, base_path)
    return chunks


def get_all_chunks(repo_name: str) -> list[dict]:
    repo_path = config.REPOS_BASE_PATH / repo_name
    if not repo_path.exists():
        return []

    all_chunks = []
    for file_path in iter_code_files(repo_path):
        chunks = chunk_file(file_path, repo_name, repo_path)
        all_chunks.extend(chunks)
    return all_chunks

"""Построчный чанкер — fallback для языков без Tree-sitter или при ошибке парсинга."""

from pathlib import Path
import config

from .base import get_language, read_file_content


def chunk_file(path: Path, repo_name: str, base_path: Path) -> list[dict]:
    content = read_file_content(path)
    language = get_language(path)
    rel_path = path.relative_to(base_path)

    chunks = []
    lines = content.split("\n")

    if len(lines) <= 50:
        chunks.append(_make_chunk(content, repo_name, rel_path, language, "file"))
    else:
        chunk_lines = []
        for line in lines:
            chunk_lines.append(line)
            if len("\n".join(chunk_lines)) > config.CHUNK_SIZE:
                chunks.append(_make_chunk("\n".join(chunk_lines[:-1]), repo_name, rel_path, language, "chunk"))
                chunk_lines = [line]
        if chunk_lines:
            chunks.append(_make_chunk("\n".join(chunk_lines), repo_name, rel_path, language, "chunk"))

    return chunks


def _make_chunk(content: str, repo: str, path: Path, language: str, typ: str) -> dict:
    return {
        "content": content,
        "metadata": {
            "repo": repo,
            "path": str(path),
            "language": language,
            "type": typ,
        },
    }

"""Семантический чанкер на Tree-sitter — границы по функциям, классам, методам."""

from pathlib import Path

from .base import get_language, get_ts_grammar, read_file_content, SEMANTIC_LANGUAGES


def _patch_chunker_registry_cache():
    """Патч: treesitter-chunker не кэширует языки из tree-sitter-language-pack,
    из-за чего при каждом файле заново грузится grammar. Кэшируем результат.
    """
    try:
        from chunker._internal.registry import LanguageRegistry

        _orig_try_load = LanguageRegistry._try_load_from_language_pack

        def _cached_try_load(self, name: str):
            if name in self._languages:
                lang, meta = self._languages[name]
                if lang is not None:
                    return lang
            lang = _orig_try_load(self, name)
            if lang is not None:
                from chunker._internal.registry import LanguageMetadata
                self._languages[name] = (lang, LanguageMetadata(name=name))
            return lang

        LanguageRegistry._try_load_from_language_pack = _cached_try_load
    except Exception:
        pass  # chunker может быть не установлен


_patch_chunker_registry_cache()


def _extract_content(chunk, source: str) -> str:
    text = getattr(chunk, "content", None) or getattr(chunk, "text", None)
    if text:
        return text
    sb = getattr(chunk, "byte_start", None) or getattr(chunk, "start_byte", None)
    eb = getattr(chunk, "byte_end", None) or getattr(chunk, "end_byte", None)
    if sb is not None and eb is not None:
        return source[sb:eb]
    return ""


def chunk_file(path: Path, repo_name: str, base_path: Path) -> list[dict]:
    language = get_language(path)
    if language not in SEMANTIC_LANGUAGES:
        return []

    content = read_file_content(path)
    rel_path = path.relative_to(base_path)
    grammar = get_ts_grammar(language)

    try:
        from chunker import chunk_text
    except ImportError:
        return []

    try:
        ts_chunks = chunk_text(content, grammar)
    except Exception:
        return []

    if not ts_chunks:
        return []

    result = []
    for c in ts_chunks:
        text = _extract_content(c, content)
        if not text or not text.strip():
            continue

        node_type = getattr(c, "node_type", "block")
        # Имя ноды (функции/класса) — прибавляем к тексту чанка как заголовок
        node_name = getattr(c, "name", None) or getattr(c, "identifier", None)
        chunk_content = f"# {node_name}\n{text}" if node_name else text
        result.append({
            "content": chunk_content,
            "metadata": {
                "repo": repo_name,
                "path": str(rel_path),
                "language": language,
                "type": node_type,
                "name": node_name or "",
            },
        })
    return result

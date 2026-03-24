"""Repo metadata stored in Qdrant collection properties."""
import logging
from rag.qdrant_client import (
    get_collection_properties,
    list_collections,
    set_collection_properties,
)

logger = logging.getLogger(__name__)


def get_metadata(name: str) -> dict:
    return get_collection_properties(name) or {}


def set_metadata(name: str, data: dict):
    set_collection_properties(name, data)


def get_enabled(name: str) -> bool:
    return get_metadata(name).get("enabled", True)


def set_enabled(name: str, enabled: bool):
    set_collection_properties(name, {"enabled": enabled})


def remove_metadata(name: str):
    pass


def format_repo_catalog_for_llm() -> str:
    """Краткий каталог включённых репозиториев для промпта LLM (id + краткое описание).

    Полную спецификацию конкретного репо запрашивай тулом get_repo_full_specification.
    Пустая строка, если нет коллекций или ни одна не включена.
    """
    names = list_collections()
    if not names:
        return ""

    blocks: list[str] = []
    for name in sorted(names):
        if not get_enabled(name):
            continue
        meta = get_metadata(name)
        display = (meta.get("display_name") or "").strip()
        short = meta.get("short_description")
        if short is not None:
            short = str(short).strip()

        lines: list[str] = [f"— `{name}` — идентификатор в индексе (аргумент repo в поиске)"]
        if display:
            lines.append(f"  Название: {display}")
        if short:
            lines.append(f"  Кратко: {short}")
        blocks.append("\n".join(lines))

    if not blocks:
        return ""

    header = (
        "Каталог репозиториев, доступных для поиска (только включённые). "
        "Для полной спецификации конкретного репо вызывай get_repo_full_specification."
    )
    return f"{header}\n\n" + "\n\n".join(blocks)


def get_repo_full_specification_text(repo: str) -> str:
    """Полная спецификация (description) одного репозитория для тула агента."""
    known = list_collections()
    if repo not in known:
        return f"Репозиторий `{repo}` не найден в индексе. Уточни идентификатор через list_indexed_repos."
    if not get_enabled(repo):
        return f"Репозиторий `{repo}` существует, но выключен и недоступен для поиска."
    meta = get_metadata(repo)
    display = (meta.get("display_name") or "").strip()
    suggested = (meta.get("suggested_name") or "").strip()
    full = (meta.get("full_description") or meta.get("description") or "").strip()
    short = (meta.get("short_description") or "").strip()

    lines: list[str] = [f"Репозиторий: `{repo}`"]
    if display:
        lines.append(f"Название: {display}")
    if suggested:
        lines.append(f"Предлагаемое название (Describer): {suggested}")
    if short:
        lines.append(f"Кратко: {short}")
    if full:
        lines.append(f"\nПолная спецификация:\n{full}")
    else:
        lines.append("Полная спецификация не задана (добавь описание в карточке репозитория).")
    return "\n".join(lines)

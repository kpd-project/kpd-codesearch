"""Repo metadata stored in Qdrant collection properties."""
import logging
from rag.qdrant_client import get_collection_properties, set_collection_properties

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

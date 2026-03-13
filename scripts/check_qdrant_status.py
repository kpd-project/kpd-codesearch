#!/usr/bin/env python3
"""Проверка статуса коллекций в Qdrant — то же, что /status в боте. Запуск: python scripts/check_qdrant_status.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import rag

def main():
    print("📊 Статус коллекций (прямой запрос к Qdrant):\n")
    for repo in config.REPOS_WHITELIST:
        if rag.collection_exists(repo):
            info = rag.get_collection_info(repo)
            print(f"  {repo}: vectors_count={info['vectors_count']}, points_count={info['points_count']}")
        else:
            print(f"  {repo}: коллекция не создана")
    print("\nЕсли числа совпадают с ответом бота — /status говорит правду.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Проверка статуса коллекций в Qdrant — то же, что /status в боте. Запуск: python scripts/check_qdrant_status.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import rag

def main():
    print("📊 Статус коллекций (прямой запрос к Qdrant):\n")
    collections = rag.list_collections()
    if not collections:
        print("  Нет коллекций.")
    else:
        for repo in collections:
            info = rag.get_collection_info(repo)
            print(f"  {repo}: vectors_count={info['vectors_count']}, points_count={info['points_count']}")
    print("\nЕсли числа совпадают с ответом бота — /status говорит правду.")

if __name__ == "__main__":
    main()

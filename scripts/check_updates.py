#!/usr/bin/env python3
"""Проверка: получает ли бот апдейты из Telegram. Запусти, пиши в группу — смотри вывод."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import httpx
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    print("TELEGRAM_BOT_TOKEN не задан в .env")
    sys.exit(1)

BASE = f"https://api.telegram.org/bot{TOKEN}"

# 1. Снять webhook
r = httpx.get(f"{BASE}/deleteWebhook", params={"drop_pending_updates": True})
print("deleteWebhook:", r.json())

# 2. Дёргаем getUpdates в цикле
offset = 0
print("\nСлушаю апдейты... Пиши в группу или в личку боту. Ctrl+C — выход.\n")
while True:
    r = httpx.get(f"{BASE}/getUpdates", params={"offset": offset, "timeout": 30})
    data = r.json()
    if not data.get("ok"):
        print("Ошибка API:", data)
        break
    for u in data.get("result", []):
        offset = u["update_id"] + 1
        msg = u.get("message") or u.get("channel_post")
        if msg:
            chat = msg.get("chat", {})
            text = (msg.get("text") or "")[:60]
            print(f"  [OK] chat_id={chat.get('id')} type={chat.get('type')} text={text!r}")
        else:
            print("  update:", u)

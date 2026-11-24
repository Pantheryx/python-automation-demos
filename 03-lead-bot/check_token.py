#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка токена бота без запуска бота.

    python check_token.py

Печатает имя бота и его username. Токен в вывод не попадает.
"""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv(".env")


def main() -> int:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        print("BOT_TOKEN не найден в .env")
        return 1
    if token.count(":") != 1 or len(token) < 40:
        print("Токен выглядит битым: ожидается формат 123456789:AA... (около 46 символов)")
        print(f"сейчас: {len(token)} символов, двоеточий: {token.count(':')}")
        return 1

    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=20)
    except requests.RequestException as error:
        print(f"Нет связи с Telegram: {type(error).__name__}")
        print("Запустите проверку на VPS или через VPN — с этого компьютера домены Telegram недоступны.")
        return 2

    data = response.json()
    if not data.get("ok"):
        print(f"Telegram ответил ошибкой: {data.get('description')}")
        return 3

    bot = data["result"]
    print(f"Токен рабочий: @{bot.get('username')} ({bot.get('first_name')})")
    print(f"ID бота: {bot.get('id')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

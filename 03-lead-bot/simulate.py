#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Прогон сценария бота без сети: тот же код, заглушка вместо Telegram.

Пишет transcript.json — список реплик для карточки портфолио.
"""

from __future__ import annotations

import json
from pathlib import Path

import bot

BASE = Path(__file__).resolve().parent
TRANSCRIPT = BASE / "transcript.json"

DIALOG: list[tuple[str, str]] = []


def fake_send(chat_id: int, text: str, keyboard=None) -> None:
    DIALOG.append(("bot", text))
    if keyboard:
        DIALOG.append(("buttons", " | ".join(button["text"] for row in keyboard for button in row)))


def fake_api(method: str, **payload):
    return {"ok": True}


bot.send = fake_send
bot.api = fake_api
bot.init_db()

states: dict = {}
user = {"id": 100001, "username": "demo_client"}


def message(text: str) -> None:
    DIALOG.append(("user", text))
    bot.handle_message({"chat": {"id": 100001}, "from": user, "text": text}, states)


def callback(code: str) -> None:
    bot.handle_callback({
        "id": "1",
        "data": code,
        "message": {"chat": {"id": 100001}},
        "from": user,
    }, states)


message("/start")
message("Максим")
message("Нужно собирать заявки с сайта в таблицу и присылать в Telegram")
callback("b2")
message("да")

TRANSCRIPT.write_text(json.dumps(DIALOG, ensure_ascii=False, indent=1), encoding="utf-8")
for role, text in DIALOG:
    print(f"[{role}] {text}")

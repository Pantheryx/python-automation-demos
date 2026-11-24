#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telegram-бот заявок: диалог → SQLite → уведомление админу.

Запуск:
    python bot.py

Переменные в .env:
    BOT_TOKEN=...
    ADMIN_ID=...
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()
API = f"https://api.telegram.org/bot{TOKEN}"
DB = Path(os.getenv("DB_PATH", BASE / "leads.db"))

log = logging.getLogger("bot")

BUDGETS = [("до 1 000 ₽", "b1"), ("1 000–5 000 ₽", "b2"), ("больше 5 000 ₽", "b3")]
STEPS = ("name", "task", "budget", "confirm")


def api(method: str, **payload):
    """Запрос к Telegram Bot API с понятной ошибкой."""
    response = requests.post(f"{API}/{method}", json=payload, timeout=30)
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"{method}: {data.get('description')}")
    return data["result"]


def init_db() -> None:
    with sqlite3.connect(DB) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL,
                username TEXT,
                name TEXT NOT NULL,
                task TEXT NOT NULL,
                budget TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL
            )"""
        )


def save_lead(user: dict, name: str, task: str, budget: str) -> int:
    with sqlite3.connect(DB) as connection:
        cursor = connection.execute(
            "INSERT INTO leads (tg_id, username, name, task, budget, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user["id"], user.get("username", ""), name, task, budget, datetime.now().isoformat(timespec="seconds")),
        )
        return int(cursor.lastrowid)


def count_leads() -> int:
    with sqlite3.connect(DB) as connection:
        return int(connection.execute("SELECT COUNT(*) FROM leads").fetchone()[0])


def send(chat_id: int, text: str, keyboard: list | None = None) -> None:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        payload["reply_markup"] = {"inline_keyboard": keyboard}
    api("sendMessage", **payload)


def budget_keyboard() -> list:
    return [[{"text": label, "callback_data": code}] for label, code in BUDGETS]


def budget_label(code: str) -> str:
    return next((label for label, key in BUDGETS if key == code), code)


def handle_message(message: dict, states: dict) -> None:
    chat_id = message["chat"]["id"]
    user = message.get("from", {})
    text = (message.get("text") or "").strip()
    state = states.setdefault(chat_id, {"step": "start"})

    if text.startswith("/start"):
        state.clear()
        state["step"] = "name"
        send(chat_id, "Здравствуйте! Помогу оставить заявку.\n\nКак вас зовут?")
        return

    if text.startswith("/cancel"):
        states.pop(chat_id, None)
        send(chat_id, "Отменил. Начать заново — /start")
        return

    if text.startswith("/leads"):
        if ADMIN_ID and str(user.get("id")) == ADMIN_ID:
            send(chat_id, f"Заявок в базе: <b>{count_leads()}</b>")
        else:
            send(chat_id, "Команда доступна только администратору.")
        return

    if state["step"] == "name":
        if not 2 <= len(text) <= 40:
            send(chat_id, "Имя — от 2 до 40 символов. Напишите ещё раз.")
            return
        state["name"] = text
        state["step"] = "task"
        send(chat_id, f"{text}, что нужно автоматизировать? Опишите в двух-трёх предложениях.")
        return

    if state["step"] == "task":
        if len(text) < 10:
            send(chat_id, "Добавьте пару деталей: что на входе и что должно получиться.")
            return
        state["task"] = text
        state["step"] = "budget"
        send(chat_id, "Какой бюджет?", budget_keyboard())
        return

    if state["step"] == "budget":
        send(chat_id, "Выберите бюджет кнопкой ниже.", budget_keyboard())
        return

    if state["step"] == "confirm":
        if text.lower() in ("да", "верно", "подтверждаю"):
            lead_id = save_lead(user, state["name"], state["task"], state["budget"])
            states.pop(chat_id, None)
            send(chat_id, f"Заявка №{lead_id} принята. Свяжусь с вами в этом чате.")
            if ADMIN_ID:
                send(
                    int(ADMIN_ID),
                    f"<b>Новая заявка №{lead_id}</b>\n"
                    f"Имя: {state['name']}\n"
                    f"Задача: {state['task']}\n"
                    f"Бюджет: {state['budget']}\n"
                    f"Контакт: @{user.get('username', '—')} (id {user.get('id')})",
                )
            return
        send(chat_id, "Напишите «да», чтобы отправить заявку, или /cancel.")
        return

    send(chat_id, "Начнём заново: /start")


def handle_callback(callback: dict, states: dict) -> None:
    chat_id = callback["message"]["chat"]["id"]
    code = callback.get("data", "")
    state = states.setdefault(chat_id, {"step": "start"})

    if state.get("step") != "budget":
        api("answerCallbackQuery", callback_query_id=callback["id"], text="Сначала заполните имя и задачу")
        return

    state["budget"] = budget_label(code)
    state["step"] = "confirm"
    api("answerCallbackQuery", callback_query_id=callback["id"], text="Бюджет сохранён")
    send(
        chat_id,
        "Проверьте заявку:\n\n"
        f"Имя: {state['name']}\n"
        f"Задача: {state['task']}\n"
        f"Бюджет: {state['budget']}\n\n"
        "Всё верно? Напишите «да».",
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not TOKEN:
        print("Нет BOT_TOKEN в .env")
        return 1

    init_db()
    me = api("getMe")
    log.info("Бот запущен: @%s", me.get("username"))

    states: dict = {}
    offset = 0
    while True:
        try:
            updates = api("getUpdates", offset=offset, timeout=25, allowed_updates=["message", "callback_query"])
        except Exception as error:  # сеть или 409 при втором экземпляре
            log.warning("getUpdates: %s", error)
            time.sleep(3)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            try:
                if "message" in update:
                    handle_message(update["message"], states)
                elif "callback_query" in update:
                    handle_callback(update["callback_query"], states)
            except Exception as error:
                log.exception("Ошибка обработки: %s", error)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Остановлен")

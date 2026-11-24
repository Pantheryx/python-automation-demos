"""Создаёт три «грязные» выгрузки для демонстрации отчёта."""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "data"
OUT.mkdir(parents=True, exist_ok=True)

PRODUCTS = [
    ("Носки с полосой", "носки", 390),
    ("Термос 500 мл", "Термосы", 1290),
    ("Рюкзак городской", "рюкзаки", 2450),
    ("Ремешок для часов", "Аксессуары", 890),
    ("Кружка керамическая", "АКСЕССУАРЫ", 640),
]
CLIENTS = ["Иван", "Мария", "ООО «Вектор»", "Анна", "Пётр", "ИП Смирнов"]
FORMATS = ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]

random.seed(42)
rows = []
start = date(2026, 8, 1)
for _ in range(60):
    product, category, price = random.choice(PRODUCTS)
    when = start + timedelta(days=random.randint(0, 89))
    qty = random.randint(1, 4)
    rows.append({
        "дата": when,
        "товар": product,
        "категория": category,
        "количество": qty,
        "сумма": price * qty,
        "клиент": random.choice(CLIENTS),
    })


def format_date(value: date, index: int) -> str:
    if index % 3 == 0:
        months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
        return f"{value.day} {months[value.month - 1]} {value.year}"
    return value.strftime(FORMATS[index % len(FORMATS)])


def format_money(value: float, index: int) -> str:
    if index % 3 == 0:
        return f"{value:,.2f}".replace(",", " ").replace(".", ",")
    if index % 3 == 1:
        return f"{value:.2f}"
    return f"{value:.0f} ₽"


for part in range(3):
    chunk = rows[part * 20:(part + 1) * 20]
    # пара дублей из предыдущей части
    if part > 0:
        chunk = chunk + rows[(part - 1) * 20:(part - 1) * 20 + 3]
    path = OUT / f"выгрузка-{part + 1}.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["дата", "товар", "категория", "количество", "сумма", "клиент"])
        for index, row in enumerate(chunk):
            writer.writerow([
                format_date(row["дата"], index + part),
                row["товар"],
                row["категория"],
                row["количество"],
                format_money(row["сумма"], index + part),
                row["клиент"],
            ])
        if part == 1:
            writer.writerow(["", "", "", "", "", ""])
            writer.writerow(["32.13.2026", "Битый товар", "Носки", "1", "abc", "Тест"])
    print(path.name, "строк:", len(chunk))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Отчёт по продажам из трёх «грязных» выгрузок → Excel с формулами.

Запуск:
    python report.py

Вход:  data/*.csv  (разные форматы дат, суммы с пробелами и запятыми, дубли)
Выход: output/report.xlsx — листы «Данные», «Сводка», «Ошибки», «Инструкция»
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

BASE = Path(__file__).resolve().parent
INPUT = BASE / "data"
OUTPUT = BASE / "output" / "report.xlsx"

MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}


@dataclass
class Sale:
    when: date
    product: str
    category: str
    qty: int
    amount: float
    client: str


def parse_date(raw: str) -> date | None:
    text = (raw or "").strip()
    if not text:
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    match = re.fullmatch(r"(\d{1,2})\s+([а-яё]+)\s+(\d{4})", text.lower())
    if match and match.group(2) in MONTHS:
        return date(int(match.group(3)), MONTHS[match.group(2)], int(match.group(1)))
    return None


def parse_money(raw: str) -> float | None:
    text = (raw or "").strip().replace("\xa0", " ").replace(" ", "")
    text = text.replace("₽", "").replace("руб.", "").replace("руб", "").strip()
    if not text:
        return None
    if "," in text and "." in text:
        text = text.replace(",", "")
    else:
        text = text.replace(",", ".")
    try:
        return round(float(text), 2)
    except ValueError:
        return None


def parse_int(raw: str) -> int | None:
    try:
        return int(float((raw or "").strip().replace(",", ".")))
    except ValueError:
        return None


def normalize_category(raw: str) -> str:
    text = (raw or "").strip().lower()
    aliases = {"носки": "Носки", "аксессуары": "Аксессуары", "рюкзаки": "Рюкзаки", "термосы": "Термосы"}
    return aliases.get(text, text.capitalize() or "Без категории")


def read_rows(folder: Path) -> tuple[list[Sale], list[str], int]:
    sales: list[Sale] = []
    errors: list[str] = []
    total = 0
    seen: set[tuple] = set()

    for path in sorted(folder.glob("*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for number, row in enumerate(csv.DictReader(handle, delimiter=";"), start=2):
                total += 1
                if not any((value or "").strip() for value in row.values()):
                    errors.append(f"{path.name}:{number} пустая строка")
                    continue

                when = parse_date(row.get("дата", ""))
                amount = parse_money(row.get("сумма", ""))
                qty = parse_int(row.get("количество", ""))
                product = (row.get("товар") or "").strip()

                if when is None:
                    errors.append(f"{path.name}:{number} дата «{row.get('дата', '')}»")
                    continue
                if amount is None:
                    errors.append(f"{path.name}:{number} сумма «{row.get('сумма', '')}»")
                    continue
                if not product:
                    errors.append(f"{path.name}:{number} нет названия товара")
                    continue

                key = (when, product.lower(), amount, (row.get("клиент") or "").strip().lower())
                if key in seen:
                    errors.append(f"{path.name}:{number} дубль {product} / {when}")
                    continue
                seen.add(key)

                sales.append(Sale(
                    when=when,
                    product=product,
                    category=normalize_category(row.get("категория", "")),
                    qty=qty or 1,
                    amount=amount,
                    client=(row.get("клиент") or "").strip() or "—",
                ))

    return sales, errors, total


def write_report(sales: list[Sale], errors: list[str], total: int) -> dict:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()

    data = workbook.active
    data.title = "Данные"
    data.append(["Дата", "Товар", "Категория", "Кол-во", "Сумма, ₽", "Клиент"])
    for sale in sorted(sales, key=lambda item: item.when):
        data.append([sale.when, sale.product, sale.category, sale.qty, sale.amount, sale.client])
    for cell in data[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3D2B")
    data.freeze_panes = "A2"
    data.auto_filter.ref = data.dimensions
    for index, width in enumerate([12, 34, 20, 10, 14, 24], start=1):
        data.column_dimensions[get_column_letter(index)].width = width

    last = data.max_row

    summary = workbook.create_sheet("Сводка")
    summary["A1"] = "Категория"
    summary["B1"] = "Заказов"
    summary["C1"] = "Выручка, ₽"
    summary["D1"] = "Средний чек, ₽"
    categories = sorted({sale.category for sale in sales})
    for row, category in enumerate(categories, start=2):
        summary.cell(row=row, column=1, value=category)
        summary.cell(row=row, column=2, value=f'=COUNTIF(Данные!$C$2:$C${last},A{row})')
        summary.cell(row=row, column=3, value=f'=SUMIF(Данные!$C$2:$C${last},A{row},Данные!$E$2:$E${last})')
        summary.cell(row=row, column=4, value=f'=IF(B{row}=0,0,C{row}/B{row})')
    total_row = len(categories) + 2
    summary.cell(row=total_row, column=1, value="Итого").font = Font(bold=True)
    summary.cell(row=total_row, column=2, value=f"=SUM(B2:B{total_row - 1})")
    summary.cell(row=total_row, column=3, value=f"=SUM(C2:C{total_row - 1})")
    summary.cell(row=total_row, column=4, value=f"=IF(B{total_row}=0,0,C{total_row}/B{total_row})")
    for index, width in enumerate([22, 12, 16, 18], start=1):
        summary.column_dimensions[get_column_letter(index)].width = width
    summary["C2"].number_format = "# ##0 ₽"
    for row in range(2, total_row + 1):
        summary.cell(row=row, column=3).number_format = "# ##0 ₽"
        summary.cell(row=row, column=4).number_format = "# ##0 ₽"

    chart = BarChart()
    chart.title = "Выручка по категориям"
    chart.height = 8
    chart.width = 16
    chart.add_data(Reference(summary, min_col=3, min_row=1, max_row=total_row - 1), titles_from_data=True)
    chart.set_categories(Reference(summary, min_col=1, min_row=2, max_row=total_row - 1))
    summary.add_chart(chart, "F2")

    issues = workbook.create_sheet("Ошибки")
    issues.append(["Что не распознано", "Строк"])
    counter = Counter(error.split(" ", 1)[-1] for error in errors) if errors else Counter({"нет ошибок": 0})
    for reason, count in counter.most_common(12):
        issues.append([reason, count])
    issues.column_dimensions["A"].width = 70
    issues.column_dimensions["B"].width = 10
    issues.conditional_formatting.add(
        f"B2:B{issues.max_row}",
        CellIsRule(operator="greaterThan", formula=["0"], fill=PatternFill("solid", fgColor="FFE2E2")),
    )

    guide = workbook.create_sheet("Инструкция")
    lines = [
        "Как обновить отчёт",
        "",
        "1. Замените файлы в папке data/ на новые выгрузки (CSV, разделитель «;»).",
        "2. Запустите: python report.py",
        "3. Откройте output/report.xlsx — файл пересобирается целиком.",
        "",
        "Если в листе «Ошибки» появились строки — проверьте формат даты и суммы во входном файле.",
        "Поддерживаемые форматы даты: 01.03.2026, 2026-03-05, 5 марта 2026.",
        "Сумма: 1234.5, 1 234,50, 1 234.50.",
    ]
    for index, line in enumerate(lines, start=1):
        cell = guide.cell(row=index, column=1, value=line)
        if index == 1:
            cell.font = Font(bold=True, size=13)
    guide.column_dimensions["A"].width = 90

    workbook.save(OUTPUT)

    revenue = sum(sale.amount for sale in sales)
    return {
        "rows_in": total,
        "rows_out": len(sales),
        "dropped": total - len(sales),
        "revenue": revenue,
        "avg": revenue / len(sales) if sales else 0,
    }


def main() -> int:
    if not INPUT.exists():
        print(f"Нет папки с данными: {INPUT}")
        return 1
    sales, errors, total = read_rows(INPUT)
    stats = write_report(sales, errors, total)
    print(f"Строк на входе: {stats['rows_in']}")
    print(f"На выходе:      {stats['rows_out']}")
    print(f"Отброшено:      {stats['dropped']} (в листе «Ошибки»)")
    print(f"Выручка:        {stats['revenue']:,.2f} ₽".replace(",", " "))
    print(f"Средний чек:    {stats['avg']:,.0f} ₽".replace(",", " "))
    print(f"Файл:           {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

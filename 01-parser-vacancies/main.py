#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Парсер вакансий портала «Работа России» (trudvsem.ru) → Excel-отчёт.

Источник открытый: https://opendata.trudvsem.ru/api/v1/vacancies
Запуск:
    python main.py --text python --limit 300 --out out/report.xlsx
"""

from __future__ import annotations

import argparse
import logging
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path

import requests
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

API = "https://opendata.trudvsem.ru/api/v1/vacancies"
USER_AGENT = "VacancyReport/1.0 (portfolio demo; open data)"
TIMEOUT = 30
RETRIES = 3

log = logging.getLogger("parser")


@dataclass
class Vacancy:
    name: str
    company: str
    region: str
    salary_min: int | None
    salary_max: int | None
    salary_mid: int | None
    employment: str
    qualification: str
    created: str
    url: str


def _int(value) -> int | None:
    if value in (None, "", 0, "0"):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def parse_item(item: dict) -> Vacancy | None:
    """Превращает один элемент ответа API в строку отчёта."""
    vacancy = item.get("vacancy") or item
    name = (vacancy.get("job-name") or "").strip()
    if not name:
        return None

    low = _int(vacancy.get("salary_min"))
    high = _int(vacancy.get("salary_max"))
    mid = None
    if low and high:
        mid = (low + high) // 2
    elif low or high:
        mid = low or high

    return Vacancy(
        name=name,
        company=((vacancy.get("company") or {}).get("name") or "").strip(),
        region=((vacancy.get("region") or {}).get("name") or "").strip(),
        salary_min=low,
        salary_max=high,
        salary_mid=mid,
        employment=(vacancy.get("employment") or "").strip(),
        qualification=(vacancy.get("qualification") or "").strip(),
        created=(vacancy.get("creation-date") or "").strip(),
        url=(vacancy.get("vac_url") or "").strip(),
    )


def fetch_page(session: requests.Session, text: str, offset: int, limit: int) -> dict:
    """Один запрос с повторами на 429/5xx."""
    params = {"text": text, "offset": offset, "limit": limit}
    last_error: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            response = session.get(API, params=params, timeout=TIMEOUT)
            if response.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {response.status_code}")
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as error:
            last_error = error
            pause = 2 ** attempt
            log.warning("Попытка %s не удалась: %s. Пауза %s с", attempt, error, pause)
            time.sleep(pause)
    raise RuntimeError(f"Источник недоступен: {last_error}")


def collect(text: str, limit: int, page_size: int = 100) -> tuple[list[Vacancy], list[str], int]:
    """Собирает вакансии по нескольким запросам и убирает дубли.

    API отдаёт максимум 100 записей на запрос и игнорирует offset при поиске,
    поэтому полная выборка собирается несколькими запросами через запятую.
    Возвращает строки, ошибки и сумму найденного по запросам.
    """
    rows: list[Vacancy] = []
    errors: list[str] = []
    total = 0
    seen: set[str] = set()
    queries = [part.strip() for part in text.split(",") if part.strip()]

    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})

        for query in queries:
            if len(rows) >= limit:
                break
            payload = fetch_page(session, query, 0, min(page_size, limit - len(rows)))
            meta = payload.get("meta") or {}
            total += int(meta.get("total") or 0)
            items = ((payload.get("results") or {}).get("vacancies") or [])
            if not items:
                errors.append(f"по запросу «{query}» ничего не найдено")
                continue

            for item in items:
                vacancy = parse_item(item)
                if vacancy is None:
                    errors.append("пропущена запись без названия вакансии")
                    continue
                key = vacancy.url or f"{vacancy.name}|{vacancy.company}|{vacancy.created}"
                if key in seen:
                    errors.append(f"дубль: {vacancy.name}")
                    continue
                seen.add(key)
                rows.append(vacancy)

            time.sleep(1.0)

    return rows, errors, total


def _median(values: list[int]) -> int | None:
    return int(statistics.median(values)) if values else None


def _style_header(sheet, columns: int) -> None:
    fill = PatternFill("solid", fgColor="1F3D2B")
    for index in range(1, columns + 1):
        cell = sheet.cell(row=1, column=index)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    sheet.freeze_panes = "A2"


def _autosize(sheet, widths: list[int]) -> None:
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width


def write_report(rows: list[Vacancy], errors: list[str], total: int, path: Path, query: str) -> dict:
    """Собирает книгу: Данные, Сводка, Ошибки. Возвращает контрольные цифры."""
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()

    data = workbook.active
    data.title = "Данные"
    headers = ["№", "Вакансия", "Компания", "Регион", "ЗП от", "ЗП до", "Средняя", "Занятость", "Квалификация", "Дата", "Ссылка"]
    data.append(headers)
    for number, row in enumerate(rows, start=1):
        data.append([number, row.name, row.company, row.region, row.salary_min, row.salary_max,
                     row.salary_mid, row.employment, row.qualification, row.created, row.url])
    _style_header(data, len(headers))
    _autosize(data, [6, 46, 38, 28, 10, 10, 10, 22, 20, 12, 60])
    data.auto_filter.ref = data.dimensions

    salaries = [row.salary_mid for row in rows if row.salary_mid]
    by_region = Counter(row.region for row in rows if row.region)
    by_company = Counter(row.company for row in rows if row.company)

    summary = workbook.create_sheet("Сводка")
    summary.append(["Показатель", "Значение"])
    summary.append(["Запрос", query])
    summary.append(["Найдено в источнике", total])
    summary.append(["Собрано строк", len(rows)])
    summary.append(["Без зарплаты", sum(1 for row in rows if not row.salary_mid)])
    summary.append(["Медиана, ₽", _median(salaries)])
    summary.append(["Средняя, ₽", int(statistics.mean(salaries)) if salaries else None])
    summary.append(["Минимум, ₽", min(salaries) if salaries else None])
    summary.append(["Максимум, ₽", max(salaries) if salaries else None])
    summary.append([])
    summary.append(["Регион", "Вакансий"])
    for region, count in by_region.most_common(10):
        summary.append([region, count])
    _style_header(summary, 2)
    _autosize(summary, [44, 18])

    start = summary.max_row + 2
    summary.cell(row=start, column=1, value="Компания").font = Font(bold=True)
    summary.cell(row=start, column=2, value="Вакансий").font = Font(bold=True)
    for company, count in by_company.most_common(10):
        start += 1
        summary.cell(row=start, column=1, value=company)
        summary.cell(row=start, column=2, value=count)

    chart = BarChart()
    chart.title = "Вакансии по регионам, топ-10"
    chart.y_axis.title = "Вакансий"
    chart.height = 9
    chart.width = 18
    region_rows = [r for r in summary.iter_rows(min_row=12, max_row=11 + min(10, len(by_region)), max_col=2)]
    if region_rows:
        data_ref = Reference(summary, min_col=2, min_row=11, max_row=11 + min(10, len(by_region)))
        cats_ref = Reference(summary, min_col=1, min_row=12, max_row=11 + min(10, len(by_region)))
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        summary.add_chart(chart, "D2")

    issues = workbook.create_sheet("Ошибки")
    issues.append(["Что произошло"])
    for line in errors or ["ошибок нет"]:
        issues.append([line])
    _style_header(issues, 1)
    _autosize(issues, [80])

    workbook.save(path)

    return {
        "rows": len(rows),
        "median": _median(salaries),
        "no_salary": sum(1 for row in rows if not row.salary_mid),
        "errors": len(errors),
        "regions": len(by_region),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Вакансии «Работа России» → Excel")
    parser.add_argument("--text", default="python", help="поисковый запрос")
    parser.add_argument("--limit", type=int, default=300, help="сколько вакансий собрать")
    parser.add_argument("--out", default="out/report.xlsx", help="путь к файлу отчёта")
    parser.add_argument("--verbose", action="store_true", help="подробный лог")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("parser.log", encoding="utf-8")],
    )

    log.info("Запрос: %s, лимит: %s", args.text, args.limit)
    rows, errors, total = collect(args.text, args.limit)
    stats = write_report(rows, errors, total, Path(args.out), args.text)

    log.info("Готово: %s строк, медиана %s ₽, без зарплаты %s",
             stats["rows"], stats["median"], stats["no_salary"])
    print(f"Файл: {Path(args.out).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

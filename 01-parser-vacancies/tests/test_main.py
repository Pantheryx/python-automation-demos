"""Проверки разбора данных без сети."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import Vacancy, parse_item, _median, _int  # noqa: E402


SAMPLE = {
    "vacancy": {
        "job-name": "Backend-разработчик (Python)",
        "company": {"name": 'ООО "Пример"'},
        "region": {"name": "Свердловская область"},
        "salary_min": 100000,
        "salary_max": 140000,
        "employment": "Полная занятость",
        "qualification": "Ведущий специалист",
        "creation-date": "2026-11-02",
        "vac_url": "https://trudvsem.ru/vacancy/card/1/2",
    }
}


class ParseTests(unittest.TestCase):
    def test_mid_salary(self):
        row = parse_item(SAMPLE)
        self.assertIsInstance(row, Vacancy)
        self.assertEqual(row.salary_mid, 120000)
        self.assertEqual(row.company, 'ООО "Пример"')

    def test_only_min(self):
        item = {"vacancy": {**SAMPLE["vacancy"], "salary_max": 0}}
        self.assertEqual(parse_item(item).salary_mid, 100000)

    def test_no_salary(self):
        item = {"vacancy": {**SAMPLE["vacancy"], "salary_min": 0, "salary_max": 0}}
        self.assertIsNone(parse_item(item).salary_mid)

    def test_empty_name_skipped(self):
        item = {"vacancy": {**SAMPLE["vacancy"], "job-name": "  "}}
        self.assertIsNone(parse_item(item))

    def test_int_parsing(self):
        self.assertEqual(_int("1 000"), None)
        self.assertEqual(_int("1500"), 1500)
        self.assertEqual(_int(None), None)
        self.assertEqual(_int("36.6"), 36)

    def test_median_even(self):
        self.assertEqual(_median([10, 20, 30, 40]), 25)

    def test_median_empty(self):
        self.assertIsNone(_median([]))


if __name__ == "__main__":
    unittest.main()

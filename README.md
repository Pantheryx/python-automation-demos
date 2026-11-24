# Python-автоматизация: три демо

Три небольших проекта на Python: парсер в Excel, отчёт из грязных выгрузок и Telegram-бот заявок.
Все данные — открытые или синтетические. Клиентских данных и секретов в репозитории нет.

| Проект | Что делает | Стек |
|---|---|---|
| [`01-parser-vacancies`](01-parser-vacancies/) | Собирает вакансии с открытого API «Работа России» в Excel со сводкой и листом ошибок | Python, requests, openpyxl, unittest |
| [`02-sales-report`](02-sales-report/) | Превращает три «грязных» CSV в один Excel-отчёт с формулами и листом ошибок | Python, openpyxl |
| [`03-lead-bot`](03-lead-bot/) | Telegram-бот заявок: диалог, SQLite, уведомление администратору | Python, Telegram Bot API, SQLite |

## Как запустить

Каждый проект запускается отдельно. Инструкции — в README внутри папки.

```bash
# парсер
cd 01-parser-vacancies
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py --text python --limit 100

# отчёт
cd 02-sales-report
pip install -r requirements.txt
python make_demo_data.py
python report.py

# бот
cd 03-lead-bot
pip install -r requirements.txt
copy .env.example .env
python simulate.py
```

## Что проверено

- Парсер: 7 тестов на разбор данных, запуск без сети.
- Отчёт: 68 строк на входе, 60 на выходе, 8 отброшенных с причиной.
- Бот: диалог из 4 шагов, запись в SQLite, уведомление администратору.

## Ограничения

- Парсер работает с открытым API и не обходит защиту.
- Отчёт рассчитан на три CSV с известной структурой.
- Бот — демо: перед продажей нужно добавить обработку сбоев и резервные копии.

## Контакты

Максим Колесниченко · Telegram: @Kalek_cool · Maksimkako90@gmail.com

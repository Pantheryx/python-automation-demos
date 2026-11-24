# Бот заявок

Telegram-бот: диалог из 4 шагов → запись в SQLite → уведомление администратору.

## Что нужно

- Python 3.11+
- токен бота от `@BotFather`
- 5 минут на настройку

## Установка

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Настройка

Скопируйте `.env.example` в `.env`:

```text
BOT_TOKEN=токен от BotFather
ADMIN_ID=ваш telegram id
```

`ADMIN_ID` можно узнать у `@userinfobot`. Без него бот работает, но уведомления не отправляются.

## Запуск

```powershell
python check_token.py   # проверить токен, бот не запускается
python bot.py
```

Если `check_token.py` пишет «Нет связи с Telegram» — домены Telegram недоступны из вашей сети. Запускайте на VPS или через VPN.

## Деплой на VPS (systemd)

```bash
apt install -y python3-venv
mkdir -p /opt/lead-bot && cd /opt/lead-bot
# скопировать bot.py, requirements.txt, .env
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

`/etc/systemd/system/lead-bot.service`:

```ini
[Unit]
Description=Lead bot
After=network.target

[Service]
WorkingDirectory=/opt/lead-bot
ExecStart=/opt/lead-bot/.venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now lead-bot
journalctl -u lead-bot -f
```

## Сценарий

1. `/start` — приветствие, вопрос об имени.
2. Имя — от 2 до 40 символов.
3. Задача — минимум 10 символов.
4. Бюджет — кнопки: до 1 000 / 1 000–5 000 / больше 5 000 ₽.
5. Подтверждение «да» → заявка в базе, номер клиенту, уведомление админу.

Команды: `/cancel` — начать заново, `/leads` — число заявок (только админ).

## Хранение

`leads.db`, таблица `leads`: id, tg_id, username, имя, задача, бюджет, статус, дата.
Резервная копия: скопировать файл `leads.db`.

## Проверка без сети

```powershell
python simulate.py
```

Прогоняет тот же код с заглушкой Telegram и печатает диалог.

## Ограничения

- long polling: один запущенный экземпляр на токен;
- токен хранится только в `.env`, в коде его нет;
- рассылок нет — только ответы в диалоге;
- для вебхука нужен домен и HTTPS.

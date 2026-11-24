# Деплой бота: три пути

Бот работает на long polling, поэтому ему нужен **постоянно включённый процесс**.
Сервисы, которые засыпают, не подходят: сообщения теряются.

## Сравнение

| Вариант | 24/7 | Данные | Карта | Цена | Итог |
|---|---|---|---|---|---|
| Fly.io Free plan | да | volume, $0.15/ГБ | **да, зарубежная** | $5 кредита, машина $2.19/мес | бесплатно, но карта РФ не пройдёт |
| Render Free | **нет, сон 15 мин** | нет, SQLite стирается | нет | 0 | не годится |
| Российский VPS | да | диск сохраняется | да, российская | 200–400 ₽/мес | самый надёжный |

Рекомендация: **VPS за 200–400 ₽/мес**. Это 3–4% бюджета, зато бот живой всегда и SQLite не теряется.
Бесплатные варианты без карты для polling-бота нормально не работают: либо сон, либо лимиты.

---

## Путь 1. VPS (рекомендую)

Провайдеры с оплатой российской картой: Timeweb Cloud, REG.RU, Aeza, Beget.
Минимальный тариф: 1 vCPU, 1 ГБ RAM, 10 ГБ SSD — этого хватает с запасом.

### Шаги

```bash
# 1. подключиться
ssh root@<IP>

# 2. зависимости
apt update && apt install -y python3-venv python3-pip

# 3. код
mkdir -p /opt/lead-bot && cd /opt/lead-bot
# скопировать bot.py, requirements.txt

# 4. окружение
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 5. секреты
nano .env
# BOT_TOKEN=...
# ADMIN_ID=...

# 6. проверка
.venv/bin/python check_token.py
.venv/bin/python bot.py      # Ctrl+C после проверки
```

### Автозапуск

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
EnvironmentFile=/opt/lead-bot/.env

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now lead-bot
systemctl status lead-bot
journalctl -u lead-bot -f
```

### Резервная копия базы

`crontab -e`:

```cron
0 3 * * * cp /opt/lead-bot/leads.db /opt/lead-bot/backup-$(date +\%F).db
```

---

## Путь 2. Fly.io (если есть зарубежная карта)

```bash
# установить flyctl, затем
fly auth signup
fly launch --no-deploy --copy-config      # использует fly.toml
fly volumes create leads_data --size 1
fly secrets set BOT_TOKEN=... ADMIN_ID=...
fly deploy
fly logs
```

Файлы `Dockerfile` и `fly.toml` уже готовы. Машина 256 МБ стоит $2.19/мес, на Free plan дают $5 — укладываемся.

Важно: после `fly launch` проверьте, что в `fly.toml` остался блок `[mounts]` и `DB_PATH=/data/leads.db`. Без volume база исчезнет при передеплое.

---

## Путь 3. Домашний ПК + VPN (что сейчас)

Работает, но: компьютер спит — бот молчит. Годится только для демонстрации клиенту.

---

## Чек-лист после деплоя

- [ ] `check_token.py` отвечает `Токен рабочий`
- [ ] `/start` в боте приходит ответ
- [ ] заявка доходит до админа
- [ ] `systemctl status lead-bot` — active (running)
- [ ] `journalctl -u lead-bot` без ошибок
- [ ] база пишется: `sqlite3 leads.db 'select count(*) from leads;'`
- [ ] резервная копия по cron создаётся

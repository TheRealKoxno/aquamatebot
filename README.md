# AquaMate — Telegram-бот для формирования привычки пить воду


## Запуск (локально)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=XXXXX
python -m waterbot.bot

Команды бота

/setgoal <мл>

/setcup <мл>

/drink [мл]

/status

/stats

/setreminder <интервал_мин> HH:MM-HH:MM

/remind_off

/settz

/reset_today

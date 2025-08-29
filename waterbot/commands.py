from datetime import timezone
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from .db import ensure_user, get_cfg, save_cfg, add_log, sum_today, weekly_stats
from .utils import parse_hm, local_now, today_bounds_local
from .reminders import schedule_reminder_job

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cfg = ensure_user(user_id)
    text = (
        "Привет! Я помогу сформировать привычку пить воду.\n\n"
        "Твоя текущая цель: <b>{goal}</b> мл/день. Стакан по умолчанию: <b>{cup}</b> мл.\n"
        "Окно напоминаний: <b>{start}-{end}</b> каждые <b>{intv}</b> мин. Часовой пояс: <b>{tz}</b>.\n\n"
        "Команды:\n"
        "/setgoal 2200 — цель в мл\n"
        "/setcup 250 — стакан\n"
        "/drink [мл] — записать воду (без числа — по умолчанию {cup})\n"
        "/status — прогресс сегодня\n"
        "/stats — статистика за 7 дней\n"
        "/setreminder 60 09:00-21:00 — включить напоминания\n"
        "/remind_off — выключить напоминания\n"
        "/settz Europe/Moscow — задать часовой пояс\n"
        "/reset_today — удалить записи за сегодня\n"
    ).format(goal=cfg.goal_ml, cup=cfg.cup_ml, start=cfg.start_hm, end=cfg.end_hm, intv=cfg.interval_min, tz=cfg.tz)
    await update.effective_chat.send_message(text, parse_mode=ParseMode.HTML)

async def setgoal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cfg = ensure_user(user_id)
    if not context.args:
        await update.effective_chat.send_message("Укажи цель в миллилитрах: /setgoal 2000")
        return
    try:
        goal = int(context.args[0])
        if goal <= 0 or goal > 10000:
            raise ValueError
    except ValueError:
        await update.effective_chat.send_message("Некорректное значение. Пример: /setgoal 2000")
        return
    cfg.goal_ml = goal
    save_cfg(cfg)
    await update.effective_chat.send_message(f"Цель обновлена: {goal} мл/день")

async def setcup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cfg = ensure_user(user_id)
    if not context.args:
        await update.effective_chat.send_message("Укажи объём стакана в мл: /setcup 250")
        return
    try:
        cup = int(context.args[0])
        if cup <= 0 or cup > 2000:
            raise ValueError
    except ValueError:
        await update.effective_chat.send_message("Некорректное значение. Пример: /setcup 250")
        return
    cfg.cup_ml = cup
    save_cfg(cfg)
    await update.effective_chat.send_message(f"Стакан по умолчанию: {cup} мл")

async def drink_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cfg = ensure_user(user_id)
    if context.args:
        try:
            amount = int(context.args[0])
            if amount <= 0 or amount > 2000:
                raise ValueError
        except ValueError:
            await update.effective_chat.send_message("Некорректный объём. Пример: /drink 250")
            return
    else:
        amount = cfg.cup_ml
    add_log(user_id, amount)
    total = sum_today(user_id, cfg)
    left = max(0, cfg.goal_ml - total)
    await update.effective_chat.send_message(
        f"Записал {amount} мл. Сегодня: {total} мл. Осталось: {left} мл.")
    
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cfg = ensure_user(user_id)
    total = sum_today(user_id, cfg)
    left = max(0, cfg.goal_ml - total)
    now = local_now(cfg).strftime("%H:%M, %d.%m")
    await update.effective_chat.send_message(
        f"Сейчас {now} ({cfg.tz}). Сегодня выпито: {total} мл из {cfg.goal_ml} мл. Осталось: {left} мл.")

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cfg = ensure_user(user_id)
    data = weekly_stats(user_id, cfg)
    lines = [f"{d}: {v} мл" for d, v in data]
    await update.effective_chat.send_message("Статистика за 7 дней:\n" + "\n".join(lines))

async def settz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cfg = ensure_user(user_id)
    if not context.args:
        await update.effective_chat.send_message(
            f"Текущий часовой пояс: {cfg.tz}. Пример: /settz Europe/Moscow")
        return
    tz = context.args[0]
    try:
        _ = ZoneInfo(tz)
    except Exception:
        await update.effective_chat.send_message("Неизвестный TZ. Примеры: Europe/Dublin, Europe/Moscow, Asia/Almaty")
        return
    cfg.tz = tz
    save_cfg(cfg)
    await update.effective_chat.send_message(f"Часовой пояс обновлён: {tz}")

async def setreminder_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cfg = ensure_user(user_id)
    if len(context.args) != 2:
        await update.effective_chat.send_message(
            "Формат: /setreminder <интервал_мин> <HH:MM-HH:MM>\nПример: /setreminder 60 09:00-21:00")
        return
    try:
        interval = int(context.args[0])
        if interval < 10 or interval > 480:
            raise ValueError
        window = context.args[1]
        start_s, end_s = window.split("-")
        _ = parse_hm(start_s)
        _ = parse_hm(end_s)
    except Exception:
        await update.effective_chat.send_message("Некорректные параметры. Пример: /setreminder 60 09:00-21:00")
        return


    cfg.interval_min = interval
    cfg.start_hm = start_s
    cfg.end_hm = end_s
    save_cfg(cfg)


    await schedule_reminder_job(context, user_id)


    await update.effective_chat.send_message(
    f"Напоминания включены: каждые {interval} мин с {start_s} до {end_s} ({cfg.tz}).")




async def remind_off_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = f"reminder_{user_id}"
    jobs = context.job_queue.get_jobs_by_name(name)
    for j in jobs:
        j.schedule_removal()
    await update.effective_chat.send_message("Напоминания выключены.")




async def reset_today_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cfg = ensure_user(user_id)
    start_local, end_local = today_bounds_local(cfg)
    start_utc = start_local.astimezone(timezone.utc).isoformat()
    end_utc = end_local.astimezone(timezone.utc).isoformat()
    from .db import get_db
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM logs WHERE user_id=? AND ts_utc>=? AND ts_utc<?",
        (user_id, start_utc, end_utc),
    )
    conn.commit()
    conn.close()
    await update.effective_chat.send_message("Записи за сегодня удалены.")




# Необязательный echo для чисел — чтобы можно было писать «250» и оно записывалось как /drink 250
async def echo_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    text = (update.message.text or "").strip()
    if text.isdigit():
        context.args = [text]
        await drink_cmd(update, context)
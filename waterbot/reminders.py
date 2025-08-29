from datetime import timedelta
from telegram.ext import ContextTypes
from .db import get_cfg, sum_today
from .utils import is_within_window




async def reminder_tick(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.data["user_id"]
    cfg = get_cfg(user_id)
    if not is_within_window(cfg):
        return
    total = sum_today(user_id, cfg)
    left = cfg.goal_ml - total
    if left <= 0:
        return
    suggestion = min(cfg.cup_ml, left)
    await context.bot.send_message(
        chat_id=user_id,
    text=(
            f"💧 Напоминание выпить воды! Осталось {left} мл до цели {cfg.goal_ml} мл.\n"
            f"Быстрая запись: /drink {suggestion}"
        ),
    )




async def schedule_reminder_job(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    cfg = get_cfg(user_id)
    name = f"reminder_{user_id}"
    for j in context.job_queue.get_jobs_by_name(name):
        j.schedule_removal()
    interval = timedelta(minutes=cfg.interval_min)
    context.job_queue.run_repeating(
        reminder_tick,
        interval=interval,
        name=name,
        first=0,
        data={"user_id": user_id},
    )
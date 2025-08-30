import os
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from .db import init_db
from .commands import (
    start_cmd, setgoal_cmd, setcup_cmd, drink_cmd, status_cmd,
    stats_cmd, settz_cmd, setreminder_cmd, remind_off_cmd, reset_today_cmd,
    echo_numbers,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("waterbot")


async def post_init(app: Application):
    init_db()
    logger.info("DB initialized")


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN env var")

    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("setgoal", setgoal_cmd))
    application.add_handler(CommandHandler("setcup", setcup_cmd))
    application.add_handler(CommandHandler("drink", drink_cmd))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(CommandHandler("settz", settz_cmd))
    application.add_handler(CommandHandler("setreminder", setreminder_cmd))
    application.add_handler(CommandHandler("remind_off", remind_off_cmd))
    application.add_handler(CommandHandler("reset_today", reset_today_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_numbers))

async def error_handler(update, context):
    import logging
    logging.getLogger("waterbot").exception("Unhandled error", exc_info=context.error)
    if update and update.effective_chat:
        try:
            await update.effective_chat.send_message("⚠️ Что-то пошло не так. Уже чиним.")
        except Exception:
            pass

    application.add_error_handler(error_handler)


    application.run_polling(close_loop=False)


if __name__ == "__main__":
    main()

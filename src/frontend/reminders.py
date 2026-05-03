import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings
from src.backend.crud_for_kd import get_users_pending_habits_for_today
from src.backend.database import AsyncSessionLocal
from src.frontend.bot import bot

logger = logging.getLogger(__name__)


async def send_daily_habit_reminders():
    async with AsyncSessionLocal() as db:
        pending_by_user = await get_users_pending_habits_for_today(db)

    for telegram_id, habits in pending_by_user.items():
        if not habits:
            continue

        reminder_text = "Напоминание: отметьте выполнение привычек за сегодня:\n"
        reminder_text += "\n".join(f"- {habit}" for habit in habits)
        try:
            await bot.send_message(telegram_id, reminder_text)
        except Exception as exc:
            logger.error(
                "Ошибка отправки напоминания пользователю %s: %s", telegram_id, exc
            )


def start_reminder_scheduler():
    scheduler = AsyncIOScheduler(timezone=settings.reminders_timezone)
    scheduler.add_job(
        send_daily_habit_reminders,
        CronTrigger(hour=settings.reminders_hour, minute=settings.reminders_minute),
        id="daily_habit_reminders",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler

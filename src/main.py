import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from config import settings
from src.backend.database import create_table

# from src.backend.auth import register_router
from src.backend.router_for_kd import router_keyboard
from src.backend.routers import router
from src.frontend.bot import bot
from src.frontend.handlers import auth_handlers, callbackhandlers, habit_handlers
from src.frontend.reminders import start_reminder_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Инициализация базы данных...")
    await create_table()

    print("Запуск Telegram-бота...")
    bot_task = asyncio.create_task(run_telegram_bot())
    scheduler = None
    if settings.reminders_enabled:
        print("Запуск планировщика напоминаний...")
        scheduler = start_reminder_scheduler()

    try:
        yield
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)
        print("Остановка Telegram-бота...")
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
        print("Бот остановлен")


app = FastAPI(lifespan=lifespan, debug=True)
app.include_router(router)
# app.include_router(register_router)
app.include_router(router_keyboard)


async def run_telegram_bot():
    """Запуск Telegram‑бота в фоновом режиме"""
    print("Telegram-бот запущен и слушает сообщения")
    await bot.infinity_polling()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

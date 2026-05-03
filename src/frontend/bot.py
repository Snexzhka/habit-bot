from functools import wraps

import httpx
from telebot.async_telebot import AsyncTeleBot

from config import settings

TOKEN = settings.token
URL = settings.url
bot = AsyncTeleBot(TOKEN)


async def make_api_request(method: str, endpoint: str, **kwargs):
    async with httpx.AsyncClient() as client:
        url = f"{URL}{endpoint}"
        response = await client.request(method, url, **kwargs)
        return response


def auth_required(func):
    @wraps(func)
    async def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id

        # Проверяем привязку Telegram ID к учётной записи
        response = await make_api_request("GET", f"/check-auth/{user_id}")

        if response.status_code == 200:
            return await func(message, *args, **kwargs)
        else:
            await bot.reply_to(
                message, "❌ Вы не авторизованы. Отправьте /login для входа."
            )

    return wrapper

import logging
import time

import httpx

from config import settings
from src.frontend.bot import bot
from src.frontend.keyboards import get_main_keyboard

logger = logging.getLogger(__name__)


logging.basicConfig(level=logging.INFO)

user_state = {}  # type: ignore
AUTH_STATE_TTL_SECONDS = 15 * 60


def _is_state_expired(state: dict) -> bool:
    created_at = state.get("created_at", 0)
    return (time.time() - created_at) > AUTH_STATE_TTL_SECONDS


@bot.message_handler(commands=["start"])
async def start(message):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.url}/api/start/{message.from_user.id}"
            )
            if response.status_code != 200:
                await bot.send_message(
                    message.chat.id,
                    "Ошибка сервера. Попробуйте позже.\n"
                    "1. Зарегистрируйтесь /register\n",
                )
                return

            user_data = response.json()
            is_authenticated = user_data.get("is_authenticated", False)
            # has_token = bool(user_data.get("token"))
            token = user_data.get("token")

            if is_authenticated and token:
                # if is_authenticated or has_token:
                username = user_data.get("username", "Пользователь")
                await bot.send_message(
                    message.chat.id, f"Добро пожаловать, {username}!"
                )
                await bot.send_message(
                    message.chat.id,
                    "Выберите действие",
                    reply_markup=get_main_keyboard(),
                )
            else:
                await bot.send_message(
                    message.chat.id,
                    "Добро пожаловать!\n\n"
                    "Я бот - трекер привычек\n"
                    "Я помогу тебе выработать полезные привычки за 21 день.\n"
                    "Отмечай выполнение каждый день,\n"
                    "следи за серией и получай напоминания\n"
                    "Для авторизации:\n"
                    "1. Зарегистрируйтесь — отправьте /register\n"
                    "2. Получите JWT-токен\n",
                )

    except Exception as e:
        await bot.send_message(
            message.chat.id,
            f"Произошла непредвиденная ошибка:{e}. Обратитесь к администратору.",
        )


@bot.message_handler(commands=["cancel"])
async def cancel_auth_flow(message):
    user_id = message.from_user.id
    if user_id in user_state:
        user_state.pop(message.from_user.id, None)
        await bot.send_message(message.chat.id, "Действие отменено")
    await start(message)
    return


@bot.message_handler(commands=["register"])
async def register(message):
    await bot.send_message(
        message.chat.id,
        "Регистрация нового пользователя.\n"
        "Введите имя пользователя:\n"
        "Для отмены отправьте /cancel",
    )
    user_state[message.from_user.id] = {
        "stage": "waiting_username",
        "created_at": time.time(),
    }


@bot.message_handler(
    func=lambda msg: user_state.get(msg.from_user.id, {}).get("stage")
    == "waiting_username"
)
async def get_username(message):
    """Получаем имя пользователя"""
    state = user_state.get(message.from_user.id)
    if not state or _is_state_expired(state):
        user_state.pop(message.from_user.id, None)
        await bot.send_message(
            message.chat.id, "Сессия регистрации истекла. Начните заново: /register"
        )
        return

    username = message.text.strip()
    if not username:
        await bot.send_message(
            message.chat.id, "Имя пользователя не может быть пустым. Попробуйте снова:"
        )
        return

    state["username"] = username
    state["stage"] = "waiting_password"
    await bot.send_message(
        message.chat.id, "Введите пароль:\n" "Для отмены введите /cancel"
    )


@bot.message_handler(
    func=lambda msg: user_state.get(msg.from_user.id, {}).get("stage")
    == "waiting_password"
)
async def get_password(message):
    """Получаем пароль и отправляем запрос в FastAPI"""
    state = user_state.get(message.from_user.id)
    if not state or _is_state_expired(state):
        user_state.pop(message.from_user.id, None)
        await bot.send_message(
            message.chat.id, "Сессия регистрации истекла. Начните заново: /register"
        )
        return

    password = message.text
    username = state["username"]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.url}/api/register",
                json={
                    "username": username,
                    "password": password,
                    "telegram_id": message.from_user.id,
                },
            )
            print(response.status_code)
            if response.status_code == 200:
                await bot.send_message(
                    message.chat.id,
                    "Регистрация успешна.\n" f"Добро пожаловать {username}!",
                    reply_markup=get_main_keyboard(),
                )
            else:
                error_detail = response.json().get("detail", "Unknown error")
                await bot.send_message(
                    message.chat.id, f"Ошибка регистрации: {error_detail}"
                )
        except Exception as e:
            await bot.send_message(
                message.chat.id, f"Ошибка подключения к серверу: {e}"
            )

    user_state.pop(message.from_user.id, None)


# @bot.message_handler(commands=['login'])
# async def login(message):
#     await bot.send_message(
#         message.chat.id,
#         "Чтобы авторизоваться, отправьте:\n"
#         "/token <ваш_JWT_токен>\n\n"
#         "Если у вас нет токена, зарегистрируйтесь /register."
#     )


# @bot.message_handler(commands=['token'])
# async def token(message):
#     try:
#         parts = message.text.strip().split(maxsplit=1)
#         if len(parts) < 2:
#             raise ValueError("Токен не указан")
#
#         token_value = parts[1].strip()
#         if not token_value:
#             raise ValueError("Токен не может быть пустым")
#
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{settings.url}/api/verify-token",
#                 params={"token": token_value}
#             )
#             if response.status_code != 200:
#                 await bot.send_message(
#                     message.chat.id,
#                     "Сервис авторизации временно недоступен. Попробуйте позже.")
#
#                 return
#
#             result = response.json()
#
#         if not result["valid"]:
#             await bot.send_message(
#                 message.chat.id,
#                 f"Ошибка: {result['error']}"
#             )
#             return
#
#         username = result['username']
#         async with httpx.AsyncClient() as client:
#             link_response = await client.post(
#                 f"{settings.url}/link-telegram",
#                 params={"telegram_id": message.from_user.id, "username": username}
#             )
#             if link_response.status_code != 200:
#                 await bot.send_message(
#                     message.chat.id,
#                     "Токен проверен, но не удалось привязать Telegram-аккаунт. Попробуйте позже.")
#
#                 return
#
#         await bot.send_message(
#             message.from_user.id,
#             f"Добро пожаловать, {username}!",
#             reply_markup=get_main_keyboard()
#         )
#
#     except ValueError as e:
#         await bot.send_message(message.chat.id, str(e))
#     except JWTError:
#         await bot.send_message(message.chat.id, "Неверный или истёкший токен")
#     except Exception:
#         await bot.send_message(
#             message.chat.id,
#             "Ошибка авторизации. Попробуйте снова позже.")
#
#
#
#

# @bot.message_handler(commands=['profile'])
# async def profile(message):
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.get(f"{settings.url}/api/start/{message.from_user.id}")
#             if response.status_code != 200:
#                 await bot.send_message(message.chat.id, "Не удалось проверить профиль.")
#                 return
#
#             user_data = response.json()
#             if user_data.get("is_authenticated") or user_data.get("token"):
#                 await bot.send_message(message.chat.id, "✅ Вы авторизованы")
#             else:
#                 await bot.send_message(
#                     message.chat.id,
#                     "Для начала авторизуйтесь: отправьте /login"
#                 )
#     except Exception:
#         await bot.send_message(message.chat.id, "Не удалось проверить профиль.")

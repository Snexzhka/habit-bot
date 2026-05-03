import json
import logging
import time

import httpx

from config import settings
from src.frontend.bot import bot
from src.frontend.keyboards import (
    get_edit_fields_keyboard,
    get_habits_delete_list_keyboard,
    get_habits_list_keyboard,
    get_habits_mark_list_keyboard,
    get_main_keyboard,
)

logger = logging.getLogger(__name__)

# In-memory состояние для создания/редактирования привычек
habit_state = {}  # type: ignore
HABIT_STATE_TTL_SECONDS = 30 * 60
CREATE_STAGES = {
    "waiting_name_of_habit",
    "waiting_target_count",
    "waiting_frequency",
    "waiting_description",
}


def _is_habit_state_expired(state: dict) -> bool:
    created_at = state.get("created_at", 0)
    return (time.time() - created_at) > HABIT_STATE_TTL_SECONDS


# ─── Главный текстовый меню-хендлер ────────────────────────────────────────


@bot.message_handler(content_types=["text"])
async def handle_menu_text(message):
    """Обрабатывает кнопки главного меню."""
    state = habit_state.get(message.from_user.id, {})
    if state and _is_habit_state_expired(state):
        habit_state.pop(message.from_user.id, None)
        await bot.send_message(
            message.chat.id, "Сессия истекла. Пожалуйста, начните действие заново."
        )
        return

    stage = state.get("stage")
    if await _route_by_stage(message, stage):
        return

    if stage:
        # Пользователь в процессе создания/удаления привычки — не мешаем FSM
        return

    text = message.text

    if text == "Просмотреть весь список":
        await _show_habits_list(message)
    elif text == "Создать":
        await _start_create_habit(message)
    elif text == "Редактировать":
        await _start_edit_habit(message)
    elif text == "Удалить":
        await _start_delete_habit(message)
    elif text == "Отметить выполнение":
        await _start_mark_today_habit(message)
    elif text == "Статистика":
        await _get_stats(message)


async def _route_by_stage(message, stage):
    """Централизованная маршрутизация входящего текста по FSM-состояниям."""
    if stage == "editing_habit":
        await handle_edit_input(message)
        return True

    if stage in CREATE_STAGES:
        await handle_habit_fsm(message)
        return True

    return False


async def _show_habits_list(message):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.url}/api/users/{message.from_user.id}/habits"
            )
            if response.status_code != 200:
                await bot.send_message(
                    message.chat.id, f"Ошибка сервера: {response.status_code}"
                )
                return

            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.error("Не удалось распарсить JSON: %s", response.text)
                await bot.send_message(
                    message.chat.id, "Ошибка: сервер вернул некорректные данные"
                )
                return

            if data:
                catalog_text = "\n".join(
                    f"{item.get('name', 'Без названия')}, "
                    f"{item.get('frequency', 'Без частоты')}, "
                    f"{item.get('description', 'Без описания')} — "
                    f"{item.get('target_count', '0')} дней"
                    for item in data
                )
                await bot.send_message(
                    message.chat.id,
                    f"Вот ваш список привычек:\n{catalog_text}",
                    reply_markup=get_main_keyboard(),
                )
            else:
                await bot.send_message(message.chat.id, "У вас пока нет привычек.")

    except Exception as e:
        await bot.send_message(message.chat.id, f"Ошибка подключения к серверу: {e}")


async def _start_create_habit(message):
    await bot.send_message(message.chat.id, "Введите название привычки:")
    habit_state[message.from_user.id] = {
        "stage": "waiting_name_of_habit",
        "created_at": time.time(),
    }


async def _start_edit_habit(message):
    telegram_id = message.from_user.id
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.url}/api/users/{telegram_id}/habits"
            )
            if response.status_code != 200:
                await bot.send_message(
                    message.chat.id, f"Ошибка сервера: {response.status_code}"
                )
                return

            try:
                habits = response.json()
            except json.JSONDecodeError:
                logger.error("Не удалось распарсить JSON: %s", response.text)
                await bot.send_message(
                    message.chat.id, "Ошибка: сервер вернул некорректные данные"
                )
                return

            if not habits:
                await bot.send_message(
                    message.chat.id, "У вас нет привычек для редактирования"
                )
                return

            await bot.send_message(
                message.chat.id,
                "Выберите привычку для редактирования:",
                reply_markup=get_habits_list_keyboard(habits),
            )
    except Exception as e:
        await bot.send_message(message.chat.id, f"Ошибка подключения к серверу: {e}")


async def _start_delete_habit(message):
    telegram_id = message.from_user.id
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.url}/api/users/{telegram_id}/habits"
            )
            if response.status_code != 200:
                await bot.send_message(
                    message.chat.id, f"Ошибка сервера: {response.status_code}"
                )
                return

            habits = response.json()

            if not habits:
                await bot.send_message(
                    message.chat.id, "У вас нет привычек для удаления"
                )
                return

            await bot.send_message(
                message.chat.id,
                "Выберите привычку для удаления:",
                reply_markup=get_habits_delete_list_keyboard(habits),
            )
    except Exception as e:
        await bot.send_message(message.chat.id, f"Ошибка подключения к серверу: {e}")


async def _start_mark_today_habit(message):
    telegram_id = message.from_user.id
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.url}/api/users/{telegram_id}/habits/active"  ###error
            )
            if response.status_code != 200:
                await bot.send_message(
                    message.chat.id, f"Ошибка сервера: {response.status_code}"
                )
                return

            habits = response.json()
            if not habits:
                await bot.send_message(
                    message.chat.id, "У вас нет привычек для отметки выполнения."
                )
                return

            await bot.send_message(
                message.chat.id,
                "Отметьте выполнение привычек за сегодня:",
                reply_markup=get_habits_mark_list_keyboard(habits),
            )
    except Exception as e:
        await bot.send_message(message.chat.id, f"Ошибка подключения к серверу: {e}")


async def _get_stats(message):
    telegram_id = message.from_user.id
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.url}/api/users/{telegram_id}/habits/stats"
        )
        if response.status_code != 200:
            await bot.send_message(
                message.chat.id, "❌ Не удалось загрузить статистику."
            )
            return
        habits = response.json()
        if not habits:
            await bot.send_message(message.chat.id, "У Вас еще нет привычек.")
            return
        text = "Ваш прогресс по привычкам (непрерывные серии):\n"
        for h in habits:
            if h["completed"]:
                status = "✅ Цель достигнута!"
            else:
                status = f"Осталось дней {h['remaining']}"
            text += f"{h['name']}: выполнено {h['streak']} из {h['target_count']} дней.{status}\n "
        await bot.send_message(message.chat.id, text, parse_mode="Markdown")


# ─── FSM: создание привычки ────────────────────────────────────────────────


@bot.message_handler(
    func=lambda msg: habit_state.get(msg.from_user.id, {}).get("stage") in CREATE_STAGES
)
async def handle_habit_fsm(message):
    """Маршрутизатор FSM-состояний создания привычки."""
    current_state = habit_state.get(message.from_user.id, {}).get("stage")

    handlers = {
        "waiting_name_of_habit": _get_name,
        "waiting_target_count": _get_target_count,
        "waiting_frequency": _get_frequency,
        "waiting_description": _get_description,
    }

    handler = handlers.get(current_state)
    if handler:
        await handler(message)


async def _get_name(message):
    name = message.text.strip()
    if not name:
        await bot.send_message(
            message.chat.id, "Название привычки не может быть пустым. Попробуйте снова:"
        )
        return

    habit_state[message.from_user.id]["name"] = name
    habit_state[message.from_user.id]["stage"] = "waiting_target_count"
    await bot.send_message(message.chat.id, "Введите количество дней выполнения:")


async def _get_target_count(message):
    try:
        target_count = int(message.text.strip())
    except ValueError:
        await bot.send_message(message.chat.id, "Введите корректное целое число дней:")
        return

    if target_count <= 0:
        await bot.send_message(
            message.chat.id,
            "Количество дней должно быть положительным. Попробуйте снова:",
        )
        return

    habit_state[message.from_user.id]["target_count"] = target_count
    habit_state[message.from_user.id]["stage"] = "waiting_frequency"
    await bot.send_message(
        message.chat.id, "Введите периодичность (например: daily, weekly):"
    )


async def _get_frequency(message):
    frequency = message.text.strip()
    if not frequency:
        await bot.send_message(
            message.chat.id, "Периодичность не может быть пустой. Попробуйте снова:"
        )
        return

    habit_state[message.from_user.id]["frequency"] = frequency
    habit_state[message.from_user.id]["stage"] = "waiting_description"
    await bot.send_message(message.chat.id, "Введите описание привычки:")


async def _get_description(message):
    description = message.text.strip()
    state = habit_state.get(message.from_user.id)

    if not state:
        await bot.send_message(
            message.chat.id,
            "Состояние потеряно. Начните создание заново.",
            reply_markup=get_main_keyboard(),
        )
        return

    name = state.get("name", "Без названия")
    target_count = state.get("target_count", 0)
    frequency = state.get("frequency", "Без частоты")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.url}{settings.prefix}/{message.from_user.id}/habits",
                json={
                    "name": name,
                    "frequency": frequency,
                    "target_count": target_count,
                    "description": description,
                },
            )

            if response.status_code == 200:
                await bot.send_message(
                    message.chat.id,
                    f"✅ Привычка «{name}» создана!\n"
                    f"Цель: {target_count} дней, периодичность: {frequency}.",
                )
                await bot.send_message(
                    message.chat.id,
                    "Выберите действие",
                    reply_markup=get_main_keyboard(),
                )
            else:
                error = response.json().get("detail", "Неизвестная ошибка")
                await bot.send_message(
                    message.chat.id,
                    f"Ошибка при создании: {error}\nПопробуйте ещё раз.",
                )
                # Не очищаем состояние — даём пользователю шанс исправить
                return

        except Exception as e:
            await bot.send_message(
                message.chat.id, f"Ошибка подключения к серверу: {e}"
            )
            return

    # Очищаем состояние только после успешного создания
    habit_state.pop(message.from_user.id, None)


# ─── FSM: редактирование привычки ──────────────────────────────────────────


@bot.message_handler(
    func=lambda msg: habit_state.get(msg.from_user.id, {}).get("stage")
    == "editing_habit"
)
async def handle_edit_input(message):
    """Обрабатывает ввод при редактировании привычки."""
    user_id = message.from_user.id
    state = habit_state.get(user_id)

    if not state:
        await bot.send_message(message.chat.id, "Сессия истекла. Начните заново.")
        return

    field = state.get("editing_field")
    habit_id = state.get("habit_id")

    if habit_id is None:
        await bot.send_message(
            message.chat.id, "Ошибка состояния. Начните редактирование заново."
        )
        habit_state.pop(user_id, None)
        return

    if not field:
        await bot.send_message(
            message.chat.id,
            "Сначала выберите поле для редактирования.",
            reply_markup=get_edit_fields_keyboard(),
        )
        return

    value = message.text.strip()

    # Определяем, нужно ли привести к int
    if field == "target_count":
        try:
            value = int(value)
        except ValueError:
            await bot.send_message(message.chat.id, "Введите корректное число дней:")
            return

    update_data = {"field": field, "value": value}

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{settings.url}/api/habits/{habit_id}", json=update_data
        )

    if response.status_code == 200:
        result = response.json()
        state.pop("editing_field", None)
        await bot.send_message(
            message.chat.id,
            f"{result.get('message', 'Привычка обновлена')}\n"
            "Выберите следующее поле для редактирования или нажмите «Готово».",
            reply_markup=get_edit_fields_keyboard(),
        )
    else:
        try:
            error = response.json().get("detail", "Неизвестная ошибка")
        except json.JSONDecodeError:
            error = f"HTTP {response.status_code}: некорректный ответ сервера"
        await bot.send_message(
            message.chat.id,
            f"Ошибка обновления: {error}\n"
            "Введите значение для этого же поля еще раз или выберите другое поле.",
            reply_markup=get_edit_fields_keyboard(),
        )

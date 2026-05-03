import logging
import time

import httpx

from config import settings
from src.frontend.bot import bot
from src.frontend.handlers.habit_handlers import habit_state
from src.frontend.keyboards import (
    get_confirm_delete_keyboard,
    get_edit_fields_keyboard,
    get_main_keyboard,
)

logging.basicConfig(level=logging.INFO)


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_habit_"))
async def select_habit_to_edit(call):
    habit_id = int(call.data.split("_")[2])
    user_id = call.from_user.id

    habit_state[user_id] = {
        "stage": "editing_habit",
        "habit_id": habit_id,
        "created_at": time.time(),
    }

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Редактирование привычки (ID: {habit_id}).\nВыберите поле:",
        reply_markup=get_edit_fields_keyboard(),
    )
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("field_"))
async def start_field_edit(call):
    user_id = call.from_user.id
    state = habit_state.get(user_id, {})

    if state.get("stage") != "editing_habit":
        await bot.answer_callback_query(call.id, "Сессия редактирования истекла")
        return

    field = call.data.removeprefix("field_")
    if field == "done":
        habit_state.pop(user_id, None)
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Редактирование завершено.",
        )
        await bot.send_message(
            call.message.chat.id,
            "Что хотите сделать дальше?",
            reply_markup=get_main_keyboard(),
        )
        await bot.answer_callback_query(call.id)
        return

    state["editing_field"] = field

    prompts = {
        "name": "Введите новое название:",
        "description": "Введите новое описание:",
        "frequency": "Введите новую частоту (например: daily, weekly):",
        "target_count": "Введите новую цель (количество дней):",
    }

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=prompts.get(field, "Введите новое значение:"),
        reply_markup=None,
    )
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_habit_"))
async def select_habit_to_delete(call):
    habit_id = int(call.data.split("_")[2])
    user_id = call.from_user.id

    habit_state[user_id] = {
        "stage": "deleting_habit",
        "habit_id": habit_id,
        "created_at": time.time(),
    }

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Вы уверены, что хотите удалить привычку?\n\nID: {habit_id}",
        reply_markup=get_confirm_delete_keyboard(habit_id),
    )
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_"))
async def confirm_delete_habit(call):
    habit_id = int(call.data.split("_")[2])
    user_id = call.from_user.id

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{settings.url}/api/habits/{habit_id}",
        )

    if response.status_code == 200:
        try:
            result = response.json()
        except ValueError:
            result = {}
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=result.get("message", "Привычка удалена"),
        )
        await bot.send_message(
            call.message.chat.id, "Что делаем дальше?", reply_markup=get_main_keyboard()
        )
    else:
        try:
            detail = response.json().get("detail", "Попробуйте позже.")
        except ValueError:
            detail = "Попробуйте позже."
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Ошибка при удалении: {detail}",
        )
        await bot.edit_message_text(
            call.message.chat.id, "Что делаем дальше?", reply_markup=get_main_keyboard()
        )

    habit_state.pop(user_id, None)
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_delete"))
async def cancel_delete_habit(call):
    user_id = call.from_user.id
    habit_state.pop(user_id, None)

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Удаление отменено.",
        reply_markup=None,
    )
    await bot.send_message(
        call.message.chat.id, "Что делаем дальше", reply_markup=get_main_keyboard()
    )
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
async def back_to_main(call):
    user_id = call.from_user.id
    habit_state.pop(user_id, None)

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Что делаем дальше?",
        reply_markup=None,
    )

    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "noop")
async def noop_callback(call):
    return await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("mark_done_"))
async def mark_habit_done_today(call):
    habit_id = int(call.data.split("_")[2])
    await _set_today_mark(call, habit_id, completed=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith("mark_skip_"))
async def mark_habit_skip_today(call):
    habit_id = int(call.data.split("_")[2])
    await _set_today_mark(call, habit_id, completed=False)


async def _set_today_mark(call, habit_id, completed: bool):
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{settings.url}/api/habits/{habit_id}/today-status",
            json={"completed": completed},
        )

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                message = data.get("message", "Статус обновлен")
            else:
                message = "Статус обновлен"
            await bot.answer_callback_query(call.id, message, show_alert=False)
        else:
            try:
                error_data = response.json()
                if isinstance(error_data, list) and error_data:
                    detail = error_data[0].get("detail", "Попробуйте позже")
                elif isinstance(error_data, dict):
                    detail = error_data.get("detail", "Попробуйте позже")
                else:
                    detail = "Попробуйте позже"
            except ValueError:
                detail = "Попробуйте позже"
            await bot.answer_callback_query(
                call.id, f"Ошибка {detail}", show_alert=True
            )

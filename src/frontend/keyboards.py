from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Создать"))
    keyboard.add(KeyboardButton("Редактировать"))
    keyboard.add(KeyboardButton("Удалить"))
    keyboard.add((KeyboardButton("Отметить выполнение")))
    keyboard.add(KeyboardButton("Просмотреть весь список"))
    keyboard.add(KeyboardButton("Статистика"))
    return keyboard


main_markup = ReplyKeyboardMarkup(resize_keyboard=True)
buttons = [
    main_markup.add(KeyboardButton("Создать")),
    main_markup.add(KeyboardButton("Редактировать")),
    main_markup.add(KeyboardButton("Удалить")),
    main_markup.add(KeyboardButton("Отметить выполнение")),
    main_markup.add(KeyboardButton("Просмотреть весь список")),
]


def get_habits_list_keyboard(habits):
    keyboard = InlineKeyboardMarkup()
    for habit in habits:
        keyboard.add(
            InlineKeyboardButton(
                f"{habit['name']} (ID: {habit['id']})",
                callback_data=f"edit_habit_{habit['id']}",
            )
        )
    keyboard.add(InlineKeyboardButton("Назад", callback_data="back_to_main"))
    return keyboard


# def get_edit_keyboard():
#     inline_keyboard = InlineKeyboardMarkup()
#     inline_keyboard.add(InlineKeyboardButton("📝 Название", callback_data="edit_name"))
#     inline_keyboard.add(InlineKeyboardButton("Описание", callback_data="edit_desc"))
#     inline_keyboard.add(InlineKeyboardButton("Частота", callback_data="edit_freq"))
#     inline_keyboard.add(InlineKeyboardButton("Количество дней", callback_data="edit_count"))
#     inline_keyboard.add(InlineKeyboardButton("Готово", callback_data="edit_done"))
#     return inline_keyboard


def get_edit_fields_keyboard():
    keyboard = InlineKeyboardMarkup()
    fields = [
        ("📝 Название", "name"),
        ("💬 Описание", "description"),
        ("🔔 Частота", "frequency"),
        ("🎯 Цель", "target_count"),
        ("✅ Готово", "done"),
    ]
    for text, field in fields:
        keyboard.add(InlineKeyboardButton(text, callback_data=f"field_{field}"))

    return keyboard


def get_habits_delete_list_keyboard(habits):
    keyboard = InlineKeyboardMarkup()
    for habit in habits:
        keyboard.add(
            InlineKeyboardButton(
                f"{habit['name']} (ID: {habit['id']})",
                callback_data=f"delete_habit_{habit['id']}",
            )
        )
    keyboard.add(InlineKeyboardButton("Назад", callback_data="back_to_main"))
    return keyboard


def get_confirm_delete_keyboard(habit_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton(
            "✅ Да, удалить", callback_data=f"confirm_delete_{habit_id}"
        ),
        InlineKeyboardButton("❌ Нет, отменить", callback_data="cancel_delete"),
    )
    return keyboard


def get_habits_mark_list_keyboard(habits):
    keyboard = InlineKeyboardMarkup()
    for habit in habits:
        habit_id = habit["id"]
        keyboard.add(
            InlineKeyboardButton(
                f"{habit['name']} (ID: {habit_id})", callback_data="noop"
            )
        )
        keyboard.row(
            InlineKeyboardButton("✅ Выполнено", callback_data=f"mark_done_{habit_id}"),
            InlineKeyboardButton(
                "❌ Не выполнено", callback_data=f"mark_skip_{habit_id}"
            ),
        )
    keyboard.add(InlineKeyboardButton("Назад", callback_data="back_to_main"))
    return keyboard

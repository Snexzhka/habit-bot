from telebot.fsm import State, StatesGroup

class MyStates(StatesGroup):
    waiting_for_input = State()
    waiting_username = State()
from aiogram.fsm.state import State, StatesGroup

class Auth(StatesGroup):
    choosing = State()

class Login(StatesGroup):
    waiting_for_password = State()

class ResetPassword(StatesGroup):
    waiting_for_secret_word = State()
    waiting_for_new_password = State()
    waiting_for_new_password_confirm = State()

class Register(StatesGroup):
    waiting_for_type = State()
    waiting_for_fullname = State()
    waiting_for_email = State()
    waiting_for_inn = State()
    waiting_for_secret_word = State()
    waiting_for_password = State()
    waiting_for_password_confirm = State()

class FillDocument(StatesGroup):
    waiting_for_field = State()

class AskQuestion(StatesGroup):
    waiting_for_question = State()
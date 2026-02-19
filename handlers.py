import re
import logging
import os
from datetime import datetime
from email_validator import validate_email, EmailNotValidError

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile, FSInputFile, InputMediaPhoto
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.exceptions import TelegramBadRequest

import keyboards
import db
from config import LAWYER_GROUP_ID
from data import CATEGORIES, DOCUMENTS_BY_KEY
from states import Auth, Login, ResetPassword, Register, FillDocument, AskQuestion
from docgen import generate_docx_from_template
from aiogram.types import Message, CallbackQuery, BufferedInputFile, FSInputFile, ErrorEvent
router = Router()

# ---------- Настройка изображений для разных типов сообщений ----------
# Ключ - идентификатор типа сообщения, значение - относительный путь к файлу
# Вы можете менять пути и добавлять новые типы по мере необходимости
MESSAGE_IMAGES = {
    "start": "./images/start.jpg",           # приветствие
    "auth_login": "./images/login.jpg",      # экран входа (ввод пароля)
    "forgot_password": "./images/forgot.jpg",# восстановление пароля
    "register_type": "./images/register.jpg",# выбор типа пользователя
    "register_fullname": "./images/register_name.jpg",
    "register_email": "./images/register_email.jpg",
    "register_inn": "./images/register_inn.jpg",
    "register_secret": "./images/register_secret.jpg",
    "register_password": "./images/register_password.jpg",
    "main_menu": "./images/main_menu.jpg",   # главное меню
    "profile": "./images/profile.jpg",       # профиль
    "support": "./images/support.jpg",       # поддержка
    "subscription": "./images/subscription.jpg",
    "categories": "./images/categories.jpg", # список категорий документов
    "documents_list": "./images/documents_list.jpg", # список документов в категории
    "ask_question": "./images/ask.jpg",      # анонимный вопрос
    "my_docs": "./images/my_docs.jpg",       # мои документы
    "cancel": "./images/cancel.jpg",          # отмена действия
    # Добавляйте свои типы по необходимости
}

async def send_photo_message(message: Message, text: str, msg_type: str = None, reply_markup=None):
    """
    Отправляет сообщение с картинкой, соответствующей типу msg_type.
    Если картинка не найдена или тип не указан, отправляет только текст.
    """
    photo_path = MESSAGE_IMAGES.get(msg_type) if msg_type else None
    try:
        if photo_path and os.path.exists(photo_path):
            photo = FSInputFile(photo_path)
            await message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=reply_markup
            )
        else:
            await message.answer(text, reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Ошибка при отправке фото (тип {msg_type}): {e}")
        await message.answer(text, reply_markup=reply_markup)

async def send_photo_callback(callback: CallbackQuery, text: str, msg_type: str = None, reply_markup=None):
    """
    Удаляет старое сообщение и отправляет новое с картинкой, соответствующей типу msg_type.
    """
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    photo_path = MESSAGE_IMAGES.get(msg_type) if msg_type else None
    try:
        if photo_path and os.path.exists(photo_path):
            photo = FSInputFile(photo_path)
            await callback.message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=reply_markup
            )
        else:
            await callback.message.answer(text, reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Ошибка при отправке фото (тип {msg_type}): {e}")
        await callback.message.answer(text, reply_markup=reply_markup)

# ---------- Старт ----------
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Auth.choosing)
    await send_photo_message(
        message,
        "👋 Добро пожаловать в юридического помощника!\n\nУ вас уже есть аккаунт?",
        msg_type="start",
        reply_markup=keyboards.get_auth_keyboard()
    )

# ---------- Вход ----------
@router.callback_query(StateFilter(Auth.choosing), F.data == "auth_login")
async def auth_login(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    telegram_id = callback.from_user.id
    user = await db.get_user(telegram_id)
    if not user:
        await send_photo_callback(
            callback,
            "❌ Пользователь с таким Telegram ID не зарегистрирован.\nНажмите /start и выберите регистрацию.",
            msg_type="auth_login"
        )
        await state.clear()
        return
    await state.set_state(Login.waiting_for_password)
    await send_photo_callback(
        callback,
        "🔑 Введите ваш пароль:",
        msg_type="auth_login",
        reply_markup=keyboards.get_login_keyboard()
    )

@router.message(StateFilter(Login.waiting_for_password))
async def process_login_password(message: Message, state: FSMContext):
    password = message.text.strip()
    telegram_id = message.from_user.id
    if await db.check_password(telegram_id, password):
        await db.update_last_active(telegram_id)
        user = await db.get_user(telegram_id)
        await send_photo_message(message, "✅ Вход выполнен успешно!", msg_type="main_menu")
        await show_main_menu(message, user['user_type'])
        await state.clear()
    else:
        await send_photo_message(
            message,
            "❌ Неверный пароль. Попробуйте ещё раз или нажмите 'Забыли пароль?'.",
            msg_type="auth_login",
            reply_markup=keyboards.get_login_keyboard()
        )

# ---------- Забыли пароль ----------
@router.callback_query(F.data == "forgot_password", StateFilter(Login.waiting_for_password))
async def forgot_password(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    telegram_id = callback.from_user.id
    user = await db.get_user(telegram_id)
    if not user:
        await send_photo_callback(callback, "❌ Пользователь не найден.", msg_type="forgot_password")
        await state.clear()
        return
    await state.set_state(ResetPassword.waiting_for_secret_word)
    await send_photo_callback(
        callback,
        "Введите ваше кодовое слово (заданное при регистрации):",
        msg_type="forgot_password",
        reply_markup=keyboards.get_cancel_keyboard()
    )

@router.message(StateFilter(ResetPassword.waiting_for_secret_word))
async def process_secret_word(message: Message, state: FSMContext):
    secret_word = message.text.strip()
    telegram_id = message.from_user.id
    if await db.check_secret_word(telegram_id, secret_word):
        await state.update_data(reset_secret_ok=True)
        await state.set_state(ResetPassword.waiting_for_new_password)
        await send_photo_message(
            message,
            "✅ Кодовое слово верно. Введите новый пароль:",
            msg_type="forgot_password",
            reply_markup=keyboards.get_cancel_keyboard()
        )
    else:
        await send_photo_message(
            message,
            "❌ Неверное кодовое слово. Попробуйте ещё раз или нажмите отмену.",
            msg_type="forgot_password",
            reply_markup=keyboards.get_cancel_keyboard()
        )

@router.message(StateFilter(ResetPassword.waiting_for_new_password))
async def process_new_password(message: Message, state: FSMContext):
    password = message.text.strip()
    if len(password) < 4:
        await send_photo_message(message, "Пароль должен быть не менее 4 символов. Введите другой:", msg_type="forgot_password")
        return
    await state.update_data(new_password=password)
    await state.set_state(ResetPassword.waiting_for_new_password_confirm)
    await send_photo_message(message, "Повторите новый пароль:", msg_type="forgot_password")

@router.message(StateFilter(ResetPassword.waiting_for_new_password_confirm))
async def process_new_password_confirm(message: Message, state: FSMContext):
    confirm = message.text.strip()
    data = await state.get_data()
    if confirm != data['new_password']:
        await send_photo_message(message, "Пароли не совпадают. Начните восстановление заново.", msg_type="forgot_password")
        await state.clear()
        await cmd_start(message, state)
        return
    telegram_id = message.from_user.id
    await db.update_password(telegram_id, data['new_password'])
    await send_photo_message(message, "✅ Пароль успешно изменён! Теперь можете войти.", msg_type="forgot_password")
    await state.clear()
    await cmd_start(message, state)

# ---------- Регистрация ----------
@router.callback_query(StateFilter(Auth.choosing), F.data == "auth_register")
async def auth_register(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    telegram_id = callback.from_user.id
    user = await db.get_user(telegram_id)
    if user:
        await send_photo_callback(
            callback,
            "❌ Вы уже зарегистрированы. Нажмите /start и выберите «Войти».",
            msg_type="register_type"
        )
        await state.clear()
        return
    await state.set_state(Register.waiting_for_type)
    await send_photo_callback(
        callback,
        "📝 Регистрация. Кто вы?",
        msg_type="register_type",
        reply_markup=keyboards.get_user_type_keyboard()
    )

@router.callback_query(StateFilter(Register.waiting_for_type), F.data.startswith("type_"))
async def register_type(callback: CallbackQuery, state: FSMContext):
    user_type = callback.data.split("_")[1]
    await state.update_data(user_type=user_type)
    await state.set_state(Register.waiting_for_fullname)
    await callback.answer()
    await send_photo_callback(
        callback,
        "Введите ваше полное имя (или наименование организации):",
        msg_type="register_fullname"
    )

@router.message(StateFilter(Register.waiting_for_fullname))
async def register_fullname(message: Message, state: FSMContext):
    full_name = message.text.strip()
    if len(full_name) < 2:
        await send_photo_message(message, "Слишком короткое имя. Введите ещё раз:", msg_type="register_fullname")
        return
    await state.update_data(full_name=full_name)
    await state.set_state(Register.waiting_for_email)
    await send_photo_message(
        message,
        "Введите ваш email:",
        msg_type="register_email",
        reply_markup=keyboards.get_cancel_keyboard()
    )

@router.message(StateFilter(Register.waiting_for_email))
async def register_email(message: Message, state: FSMContext):
    email = message.text.strip()
    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError:
        await send_photo_message(message, "Неверный формат email. Попробуйте ещё раз:", msg_type="register_email")
        return
    await state.update_data(email=email)
    data = await state.get_data()
    if data['user_type'] == "legal":
        await state.set_state(Register.waiting_for_inn)
        await send_photo_message(
            message,
            "Введите ИНН организации (или отправьте 'пропустить'):",
            msg_type="register_inn",
            reply_markup=keyboards.get_cancel_keyboard()
        )
    else:
        await state.set_state(Register.waiting_for_secret_word)
        await send_photo_message(
            message,
            "Придумайте кодовое слово для восстановления пароля:",
            msg_type="register_secret",
            reply_markup=keyboards.get_cancel_keyboard()
        )

@router.message(StateFilter(Register.waiting_for_inn))
async def register_inn(message: Message, state: FSMContext):
    inn = message.text.strip()
    if inn.lower() == "пропустить":
        inn = None
    else:
        if not inn.isdigit() or len(inn) not in (10, 12):
            await send_photo_message(
                message,
                "ИНН должен содержать 10 или 12 цифр. Попробуйте ещё раз или введите 'пропустить':",
                msg_type="register_inn"
            )
            return
    await state.update_data(inn=inn)
    await state.set_state(Register.waiting_for_secret_word)
    await send_photo_message(
        message,
        "Придумайте кодовое слово для восстановления пароля:",
        msg_type="register_secret",
        reply_markup=keyboards.get_cancel_keyboard()
    )

@router.message(StateFilter(Register.waiting_for_secret_word))
async def register_secret_word(message: Message, state: FSMContext):
    secret_word = message.text.strip()
    if len(secret_word) < 2:
        await send_photo_message(message, "Кодовое слово должно быть не менее 2 символов. Введите ещё раз:", msg_type="register_secret")
        return
    await state.update_data(secret_word=secret_word)
    await state.set_state(Register.waiting_for_password)
    await send_photo_message(
        message,
        "Придумайте пароль:",
        msg_type="register_password",
        reply_markup=keyboards.get_cancel_keyboard()
    )

@router.message(StateFilter(Register.waiting_for_password))
async def register_password(message: Message, state: FSMContext):
    password = message.text.strip()
    if len(password) < 4:
        await send_photo_message(message, "Пароль должен быть не менее 4 символов. Придумайте другой:", msg_type="register_password")
        return
    await state.update_data(password=password)
    await state.set_state(Register.waiting_for_password_confirm)
    await send_photo_message(message, "Повторите пароль:", msg_type="register_password")

@router.message(StateFilter(Register.waiting_for_password_confirm))
async def register_password_confirm(message: Message, state: FSMContext):
    confirm = message.text.strip()
    data = await state.get_data()
    if confirm != data['password']:
        await send_photo_message(message, "Пароли не совпадают. Начните регистрацию заново.", msg_type="register_password")
        await state.clear()
        await cmd_start(message, state)
        return
    telegram_id = message.from_user.id
    await db.create_user(
        telegram_id=telegram_id,
        user_type=data['user_type'],
        full_name=data['full_name'],
        email=data['email'],
        password=data['password'],
        secret_word=data['secret_word'],
        inn=data.get('inn')
    )
    await send_photo_message(message, "✅ Регистрация завершена! Выполнен автоматический вход.", msg_type="main_menu")
    await show_main_menu(message, data['user_type'])
    await state.clear()

# ---------- Показать главное меню ----------
async def show_main_menu(message: Message, user_type: str):
    await send_photo_message(
        message,
        "Главное меню:",
        msg_type="main_menu",
        reply_markup=keyboards.get_main_keyboard(user_type)
    )

# ---------- Обработчики меню ----------
@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    user = await db.get_user(callback.from_user.id)
    if user:
        await send_photo_callback(
            callback,
            "Главное меню:",
            msg_type="main_menu",
            reply_markup=keyboards.get_main_keyboard(user['user_type'])
        )
    else:
        await cmd_start(callback.message, state)

@router.callback_query(F.data == "menu_profile")
async def show_profile(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка: пользователь не найден")
        return

    text = (
        f"👤 <b>Профиль</b>\n\n"
        f"🆔 Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"📛 Имя: {user['full_name']}\n"
        f"📧 Email: {user['email']}\n"
        f"👥 Тип: {user['user_type']}\n"
    )
    if user['inn']:
        text += f"🏢 ИНН: {user['inn']}\n"
    text += f"📅 Зарегистрирован: {user['created_at'][:10]}"

    await callback.answer()
    await send_photo_callback(
        callback,
        text,
        msg_type="profile",
        reply_markup=keyboards.get_profile_keyboard()
    )

@router.callback_query(F.data == "logout")
async def logout(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await send_photo_callback(
        callback,
        "🚪 Вы вышли из аккаунта.\nНапишите /start, чтобы войти снова.",
        msg_type="start"
    )

@router.callback_query(F.data == "menu_support")
async def show_support(callback: CallbackQuery):
    await callback.answer()
    await send_photo_callback(
        callback,
        "🆘 <b>Поддержка</b>\n\n"
        "По всем вопросам пишите: @your_support_username\n"
        "Или на email: support@juristbot.ru",
        msg_type="support",
        reply_markup=keyboards.get_back_to_main_keyboard()
    )

@router.callback_query(F.data == "menu_subscription")
async def show_subscription(callback: CallbackQuery):
    await callback.answer()
    await send_photo_callback(
        callback,
        "💳 <b>Подписка</b>\n\n"
        "Бесплатный тариф: до 5 документов в месяц.\n"
        "Премиум: 500 руб/мес – неограниченно.\n\n"
        "Оплата через Telegram Stars (скоро).",
        msg_type="subscription",
        reply_markup=keyboards.get_back_to_main_keyboard()
    )

@router.callback_query(F.data == "menu_create_doc")
async def show_categories(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await callback.answer("Сначала завершите текущее действие.", show_alert=True)
        return
    await callback.answer()
    await send_photo_callback(
        callback,
        "📂 Выберите категорию документа:",
        msg_type="categories",
        reply_markup=keyboards.get_categories_keyboard()
    )

@router.callback_query(F.data.startswith("cat_"))
async def show_category(callback: CallbackQuery, state: FSMContext):
    cat_id = callback.data[4:]
    if cat_id not in CATEGORIES:
        await callback.answer("Категория не найдена", show_alert=True)
        return
    await callback.answer()
    await send_photo_callback(
        callback,
        f"📂 Категория: {CATEGORIES[cat_id]}\nВыберите нужный документ:",
        msg_type="documents_list",
        reply_markup=keyboards.get_category_keyboard(cat_id)
    )

@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery):
    await callback.answer()
    await send_photo_callback(
        callback,
        "📂 Выберите категорию документа:",
        msg_type="categories",
        reply_markup=keyboards.get_categories_keyboard()
    )

@router.callback_query(F.data.startswith("doc_"))
async def start_fill_document(callback: CallbackQuery, state: FSMContext):
    doc_key = callback.data[4:]
    doc_info = DOCUMENTS_BY_KEY.get(doc_key)
    if not doc_info:
        await callback.answer("Документ не найден", show_alert=True)
        return

    _, doc_name, template_text, fields = doc_info

    await state.set_state(FillDocument.waiting_for_field)
    await state.update_data(
        doc_key=doc_key,
        doc_name=doc_name,
        template=template_text,
        fields=fields,
        field_index=0,
        collected={}
    )

    await callback.answer()
    await ask_next_field(callback.message, state)

async def ask_next_field(message: Message, state: FSMContext):
    data = await state.get_data()
    fields = data['fields']
    idx = data['field_index']

    if idx >= len(fields):
        await generate_and_send_document(message, state)
        return

    field = fields[idx]
    # Для полей документа можно использовать отдельный тип или общий
    await send_photo_message(
        message,
        field['prompt'],
        msg_type="documents_list",  # или можно создать отдельный тип, например "document_field"
        reply_markup=keyboards.get_cancel_keyboard()
    )

@router.message(StateFilter(FillDocument.waiting_for_field))
async def process_field_input(message: Message, state: FSMContext):
    data = await state.get_data()
    fields = data['fields']
    idx = data['field_index']
    field = fields[idx]

    collected = data.get('collected', {})
    collected[field['name']] = message.text
    await state.update_data(collected=collected, field_index=idx + 1)

    await ask_next_field(message, state)

async def generate_and_send_document(message: Message, state: FSMContext):
    data = await state.get_data()
    doc_key = data['doc_key']
    doc_name = data['doc_name']
    template_text = data['template']
    collected = data['collected']
    telegram_id = message.from_user.id

    try:
        file_stream = generate_docx_from_template(template_text, collected)
    except Exception as e:
        await send_photo_message(message, f"❌ Ошибка при генерации документа: {e}", msg_type="cancel")
        await state.clear()
        return

    filename = f"{doc_key}.docx"
    await message.answer_document(
        BufferedInputFile(file_stream.read(), filename=filename),
        caption=f"✅ Ваш документ «{doc_name}» готов!"
    )

    await db.add_document(telegram_id, doc_key, doc_name)

    await state.clear()
    user = await db.get_user(telegram_id)
    await show_main_menu(message, user['user_type'])

@router.callback_query(F.data == "menu_my_docs")
async def show_my_docs(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    docs = await db.get_user_documents(telegram_id)
    if not docs:
        await callback.answer("У вас пока нет сохранённых документов.", show_alert=True)
        return
    await callback.answer()
    await send_photo_callback(
        callback,
        "📁 Ваши документы:",
        msg_type="my_docs",
        reply_markup=keyboards.get_my_docs_keyboard(docs)
    )

@router.callback_query(F.data.startswith("my_doc_"))
async def show_my_document(callback: CallbackQuery):
    doc_id = int(callback.data.split("_")[2])
    await callback.answer("Просмотр документа временно недоступен", show_alert=True)

@router.callback_query(F.data == "menu_ask")
async def ask_question_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AskQuestion.waiting_for_question)
    await send_photo_callback(
        callback,
        "❓ Напишите ваш вопрос анонимно. Он будет передан нашим юристам.\n"
        "Ответ придёт в этот чат, как только юрист ответит.",
        msg_type="ask_question",
        reply_markup=keyboards.get_cancel_keyboard()
    )

@router.message(StateFilter(AskQuestion.waiting_for_question))
async def process_question(message: Message, state: FSMContext):
    question = message.text.strip()
    if len(question) < 10:
        await send_photo_message(message, "Слишком короткий вопрос. Опишите ситуацию подробнее.", msg_type="ask_question")
        return

    telegram_id = message.from_user.id
    await db.add_question(telegram_id, question)

    if LAWYER_GROUP_ID:
        try:
            await message.bot.send_message(
                LAWYER_GROUP_ID,
                f"❓ Новый вопрос от пользователя {telegram_id}:\n\n{question}"
            )
        except Exception as e:
            print(f"Не удалось отправить в группу юристов: {e}")

    await send_photo_message(
        message,
        "✅ Ваш вопрос передан юристам. Ожидайте ответа (обычно в течение дня).",
        msg_type="ask_question"
    )
    await state.clear()
    user = await db.get_user(telegram_id)
    await show_main_menu(message, user['user_type'])

@router.callback_query(F.data == "menu_check_org")
async def check_org(callback: CallbackQuery):
    await callback.answer("Функция в разработке", show_alert=True)

@router.callback_query(F.data == "menu_knowledge_base")
async def knowledge_base(callback: CallbackQuery):
    await callback.answer("База знаний появится позже", show_alert=True)

@router.callback_query(F.data == "menu_client_questions")
async def client_questions(callback: CallbackQuery):
    await callback.answer("Для юристов (в разработке)", show_alert=True)

# ---------- Отмена действия ----------
@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    current_state = await state.get_state()
    await state.clear()

    if current_state in (Login.waiting_for_password, ResetPassword.waiting_for_secret_word, ResetPassword.waiting_for_new_password, ResetPassword.waiting_for_new_password_confirm):
        await send_photo_callback(
            callback,
            "❌ Действие отменено. Нажмите /start для выбора действия.",
            msg_type="cancel"
        )
        return

    user = await db.get_user(callback.from_user.id)
    if user:
        await send_photo_callback(
            callback,
            "Действие отменено. Главное меню:",
            msg_type="main_menu",
            reply_markup=keyboards.get_main_keyboard(user['user_type'])
        )
    else:
        await send_photo_callback(
            callback,
            "Действие отменено. Напишите /start для входа.",
            msg_type="start"
        )

# ---------- Команда /cancel ----------
@router.message(Command("cancel"), StateFilter(default_state))
async def cmd_cancel_no_state(message: Message):
    await send_photo_message(message, "Нет активного действия.", msg_type="cancel")

@router.message(Command("cancel"))
async def cmd_cancel_any_state(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)
    if user:
        await show_main_menu(message, user['user_type'])
    else:
        await send_photo_message(message, "Действие отменено. Напишите /start для входа.", msg_type="start")

# ---------- Глобальный обработчик ошибок ----------
@router.errors()
async def error_handler(event: ErrorEvent):
    logging.error(f"Ошибка: {event.exception}")
    try:
        if event.update.message:
            await send_photo_message(
                event.update.message,
                "❌ Произошла внутренняя ошибка. Попробуйте позже или напишите /start.",
                msg_type="cancel"
            )
        elif event.update.callback_query:
            await event.update.callback_query.answer("Ошибка", show_alert=True)
            await send_photo_callback(
                event.update.callback_query,
                "❌ Произошла внутренняя ошибка. Попробуйте позже.",
                msg_type="cancel"
            )
    except:
        pass
    return True

# ---------- Обработчик неизвестных callback'ов ----------
@router.callback_query()
async def unknown_callback(callback: CallbackQuery):
    await callback.answer("Неизвестная команда", show_alert=True)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from data import CATEGORIES, DOCUMENTS

def get_auth_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🔑 Войти", callback_data="auth_login"),
        InlineKeyboardButton(text="📝 Зарегистрироваться", callback_data="auth_register"),
    )
    builder.adjust(1)
    return builder.as_markup()

def get_login_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для экрана ввода пароля с кнопкой 'Забыли пароль?'."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="❓ Забыли пароль?", callback_data="forgot_password"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_action"),
    )
    builder.adjust(1)
    return builder.as_markup()

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_action"))
    return builder.as_markup()

def get_user_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="👤 Физическое лицо", callback_data="type_individual"),
        InlineKeyboardButton(text="🏢 Юридическое лицо", callback_data="type_legal"),
        InlineKeyboardButton(text="⚖️ Юрист", callback_data="type_lawyer"),
    )
    builder.adjust(1)
    return builder.as_markup()

def get_main_keyboard(user_type: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if user_type == "individual":
        builder.add(
            InlineKeyboardButton(text="📄 Создать документ", callback_data="menu_create_doc"),
            InlineKeyboardButton(text="📁 Мои документы", callback_data="menu_my_docs"),
            InlineKeyboardButton(text="❓ Анонимный вопрос", callback_data="menu_ask"),
            InlineKeyboardButton(text="🆘 Поддержка", callback_data="menu_support"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="menu_profile"),
            InlineKeyboardButton(text="💳 Подписка", callback_data="menu_subscription"),
        )
    elif user_type == "legal":
        builder.add(
            InlineKeyboardButton(text="📄 Создать документ", callback_data="menu_create_doc"),
            InlineKeyboardButton(text="📁 Мои документы", callback_data="menu_my_docs"),
            InlineKeyboardButton(text="🔍 Проверить контрагента", callback_data="menu_check_org"),
            InlineKeyboardButton(text="🆘 Поддержка", callback_data="menu_support"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="menu_profile"),
            InlineKeyboardButton(text="💳 Подписка", callback_data="menu_subscription"),
        )
    elif user_type == "lawyer":
        builder.add(
            InlineKeyboardButton(text="📄 Создать документ", callback_data="menu_create_doc"),
            InlineKeyboardButton(text="📁 Мои документы", callback_data="menu_my_docs"),
            InlineKeyboardButton(text="📚 База знаний", callback_data="menu_knowledge_base"),
            InlineKeyboardButton(text="❓ Вопросы клиентов", callback_data="menu_client_questions"),
            InlineKeyboardButton(text="🆘 Поддержка", callback_data="menu_support"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="menu_profile"),
        )
    else:
        builder.add(InlineKeyboardButton(text="📄 Документы", callback_data="global_documents"))
    builder.adjust(1)
    return builder.as_markup()

def get_categories_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat_id, cat_name in CATEGORIES.items():
        builder.add(InlineKeyboardButton(text=cat_name, callback_data=f"cat_{cat_id}"))
    builder.add(InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main"))
    builder.adjust(1)
    return builder.as_markup()

def get_category_keyboard(cat_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    documents = DOCUMENTS.get(cat_id, [])
    for doc_key, doc_name, _, _ in documents:
        builder.add(InlineKeyboardButton(text=doc_name, callback_data=f"doc_{doc_key}"))
    builder.add(InlineKeyboardButton(text="🔙 К категориям", callback_data="back_to_categories"))
    builder.adjust(1)
    return builder.as_markup()

def get_my_docs_keyboard(docs_list: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for doc in docs_list:
        builder.add(InlineKeyboardButton(
            text=f"{doc['doc_name']} ({doc['created_at'][:10]})",
            callback_data=f"my_doc_{doc['id']}"
        ))
    builder.add(InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main"))
    builder.adjust(1)
    return builder.as_markup()

def get_back_to_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main"))
    return builder.as_markup()

def get_profile_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main"),
        InlineKeyboardButton(text="🚪 Выйти", callback_data="logout"),
    )
    builder.adjust(1)
    return builder.as_markup()
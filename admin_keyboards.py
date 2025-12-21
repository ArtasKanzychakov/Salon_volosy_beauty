# admin_keyboards.py - Клавиатуры для админ-панели

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_main_menu():
    """Главное меню админ-панели"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📤 Загрузить фото")],
            [KeyboardButton(text="🗑 Удалить фото")],
            [KeyboardButton(text="📊 Статус фото")],
            [KeyboardButton(text="🔙 Выйти из админки")]
        ],
        resize_keyboard=True
    )
    return kb

def get_admin_upload_menu():
    """Меню загрузки фото"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Продолжить загрузку")],
            [KeyboardButton(text="📊 Статус загрузки")],
            [KeyboardButton(text="🔙 Назад в админку")]
        ],
        resize_keyboard=True
    )
    return kb

def get_admin_delete_menu():
    """Меню удаления фото"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🗑 Выбрать для удаления")],
            [KeyboardButton(text="🔙 Назад в админку")]
        ],
        resize_keyboard=True
    )
    return kb

def get_photo_categories_menu():
    """Меню категорий фото"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧴 Тело")],
            [KeyboardButton(text="💇 Волосы - общие")],
            [KeyboardButton(text="👱‍♀️ Блондинки")],
            [KeyboardButton(text="🎨 Окрашенные")],
            [KeyboardButton(text="🎨 Оттеночные маски")],
            [KeyboardButton(text="🖼 Коллажи")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )
    return kb

def get_body_photos_menu():
    """Фото для тела"""
    buttons = [
        [KeyboardButton(text="Молочко для тела")],
        [KeyboardButton(text="Гидрофильное масло")],
        [KeyboardButton(text="Крем суфле")],
        [KeyboardButton(text="Скраб для тела")],
        [KeyboardButton(text="Гель для душа")],
        [KeyboardButton(text="Баттер для тела")],
        [KeyboardButton(text="Гиалуроновая кислота")],
        [KeyboardButton(text="🔙 К категориям")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_hair_common_menu():
    """Общие фото для волос"""
    buttons = [
        [KeyboardButton(text="Биолипидный спрей")],
        [KeyboardButton(text="Сухое масло спрей")],
        [KeyboardButton(text="Масло ELIXIR")],
        [KeyboardButton(text="Молочко для волос")],
        [KeyboardButton(text="Масло концентрат")],
        [KeyboardButton(text="Флюид для волос")],
        [KeyboardButton(text="Шампунь реконстракт")],
        [KeyboardButton(text="Маска реконстракт")],
        [KeyboardButton(text="Протеиновый крем")],
        [KeyboardButton(text="🔙 К категориям")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_blonde_photos_menu():
    """Фото для блондинок"""
    buttons = [
        [KeyboardButton(text="Шампунь для осветленных волос")],
        [KeyboardButton(text="Кондиционер для осветленных волос")],
        [KeyboardButton(text="Маска для осветленных волос")],
        [KeyboardButton(text="🔙 К категориям")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_colored_photos_menu():
    """Фото для окрашенных волос"""
    buttons = [
        [KeyboardButton(text="Шампунь для окра
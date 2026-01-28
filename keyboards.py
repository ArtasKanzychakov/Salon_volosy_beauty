"""
KEYBOARDS.PY - Клавиатуры для бота
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import config

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="💇‍♀️ Волосы"))
    builder.add(KeyboardButton(text="🧴 Тело"))
    builder.add(KeyboardButton(text="❓ Помощь"))
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

def back_to_menu_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для возврата в меню"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="↩️ Назад"))
    builder.add(KeyboardButton(text="🏠 В главное меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def selection_complete_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура после завершения подборки"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="💇‍♀️ Новая подборка волос"))
    builder.add(KeyboardButton(text="🧴 Новая подборка тела"))
    builder.add(KeyboardButton(text="🏠 В главное меню"))
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

def body_goals_keyboard() -> ReplyKeyboardMarkup:
    """Цели ухода за телом"""
    builder = ReplyKeyboardBuilder()
    for goal in config.BODY_GOALS:
        builder.add(KeyboardButton(text=goal))
    builder.add(KeyboardButton(text="↩️ Назад"))
    builder.adjust(1, 1, 1)
    return builder.as_markup(resize_keyboard=True)

def hair_type_keyboard() -> ReplyKeyboardMarkup:
    """Тип волос"""
    builder = ReplyKeyboardBuilder()
    for hair_type in config.HAIR_TYPES:
        builder.add(KeyboardButton(text=hair_type))
    builder.add(KeyboardButton(text="↩️ Назад"))
    builder.adjust(1, 1, 1)
    return builder.as_markup(resize_keyboard=True)

def hair_problems_keyboard(selected_problems: list = None) -> ReplyKeyboardMarkup:
    """Проблемы волос (мультивыбор)"""
    if selected_problems is None:
        selected_problems = []

    builder = ReplyKeyboardBuilder()

    for problem in config.HAIR_PROBLEMS:
        prefix = "✅ " if problem in selected_problems else "☐ "
        builder.add(KeyboardButton(text=f"{prefix}{problem}"))

    builder.add(KeyboardButton(text="✅ Готово"))
    builder.add(KeyboardButton(text="↩️ Назад"))
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup(resize_keyboard=True)

def scalp_type_keyboard() -> ReplyKeyboardMarkup:
    """Тип кожи головы"""
    builder = ReplyKeyboardBuilder()
    for scalp_type in config.SCALP_TYPES:
        builder.add(KeyboardButton(text=scalp_type))
    builder.add(KeyboardButton(text="↩️ Назад"))
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

def hair_volume_keyboard() -> ReplyKeyboardMarkup:
    """Объем волос"""
    builder = ReplyKeyboardBuilder()
    for volume in config.HAIR_VOLUME:
        builder.add(KeyboardButton(text=volume))
    builder.add(KeyboardButton(text="↩️ Назад"))
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

def hair_color_keyboard(hair_type: str) -> ReplyKeyboardMarkup:
    """Цвет волос (только для окрашенных)"""
    colors = config.get_hair_colors(hair_type)
    builder = ReplyKeyboardBuilder()

    for color in colors:
        builder.add(KeyboardButton(text=color))

    builder.add(KeyboardButton(text="↩️ Назад"))
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

# ==================== АДМИН-КЛАВИАТУРЫ ====================

def admin_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню админки"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📸 Получить file_id"))
    builder.add(KeyboardButton(text="📊 Проверить фото"))
    builder.add(KeyboardButton(text="🏠 В главное меню"))
    builder.adjust(1, 1, 1)
    return builder.as_markup(resize_keyboard=True)

def admin_category_keyboard() -> ReplyKeyboardMarkup:
    """Выбор категории для админки"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="💇‍♀️ Волосы"))
    builder.add(KeyboardButton(text="🧴 Тело"))
    builder.add(KeyboardButton(text="↩️ Назад"))
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

def admin_subcategory_keyboard(category: str) -> ReplyKeyboardMarkup:
    """Выбор подкатегории для админки"""
    builder = ReplyKeyboardBuilder()

    if category == "волосы":
        subcategories = config.PHOTO_STRUCTURE["волосы"].keys()
    else:
        subcategories = config.PHOTO_STRUCTURE["тело"].keys()

    for subcategory in subcategories:
        builder.add(KeyboardButton(text=subcategory))

    builder.add(KeyboardButton(text="↩️ Назад"))
    builder.adjust(1, 1, 1)
    return builder.as_markup(resize_keyboard=True)

def admin_products_keyboard(category: str, subcategory: str) -> ReplyKeyboardMarkup:
    """Выбор продукта для получения file_id"""
    builder = ReplyKeyboardBuilder()

    products = config.PHOTO_STRUCTURE[category][subcategory]

    for product_key, display_name in products:
        builder.add(KeyboardButton(text=display_name))

    builder.add(KeyboardButton(text="↩️ Назад"))
    builder.adjust(1, 1, 1)
    return builder.as_markup(resize_keyboard=True)
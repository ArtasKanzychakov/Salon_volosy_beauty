from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
import config

def main_kb():
    """Главная клавиатура"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="💇‍♀️ Волосы"))
    builder.add(KeyboardButton(text="🧴 Тело"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def back_to_start_kb():
    """Клавиатура для возврата в начало"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="👈 Назад"))
    return builder.as_markup(resize_keyboard=True)

def body_goal_kb():
    """Клавиатура для выбора цели ухода за телом"""
    builder = ReplyKeyboardBuilder()
    for goal in config.BODY_GOALS:
        builder.add(KeyboardButton(text=goal))
    builder.add(KeyboardButton(text="👈 Назад"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def hair_type_kb():
    """Клавиатура для выбора типа волос"""
    builder = ReplyKeyboardBuilder()
    for hair_type in config.HAIR_TYPES:
        builder.add(KeyboardButton(text=hair_type))
    builder.add(KeyboardButton(text="👈 Назад"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def hair_problems_kb(selected: list):
    """Клавиатура для выбора проблем волос (мультиселект)"""
    builder = ReplyKeyboardBuilder()
    
    for problem in config.HAIR_PROBLEMS:
        prefix = "✅ " if problem in selected else "☐ "
        builder.add(KeyboardButton(text=f"{prefix}{problem}"))
    
    builder.add(KeyboardButton(text="✅ Готово"))
    builder.add(KeyboardButton(text="👈 Назад"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def scalp_type_kb():
    """Клавиатура для выбора типа кожи головы"""
    builder = ReplyKeyboardBuilder()
    for scalp_type in config.SCALP_TYPES:
        builder.add(KeyboardButton(text=scalp_type))
    builder.add(KeyboardButton(text="👈 Назад"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def hair_volume_kb():
    """Клавиатура для выбора объема"""
    builder = ReplyKeyboardBuilder()
    for volume in config.HAIR_VOLUME:
        builder.add(KeyboardButton(text=volume))
    builder.add(KeyboardButton(text="👈 Назад"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def hair_color_kb(hair_type: str):
    """Клавиатура для выбора цвета волос"""
    colors = config.get_hair_colors(hair_type)
    builder = ReplyKeyboardBuilder()
    
    for color in colors:
        builder.add(KeyboardButton(text=color))
    
    builder.add(KeyboardButton(text="👈 Назад"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# ==================== АДМИН-КЛАВИАТУРЫ ====================

def admin_category_kb():
    """Клавиатура для выбора категории в админ-панели"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="💇‍♀️ Волосы"))
    builder.add(KeyboardButton(text="🧴 Тело"))
    builder.add(KeyboardButton(text="❌ Выход"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def admin_products_kb(products: list):
    """Клавиатура для выбора продукта в админ-панели"""
    builder = ReplyKeyboardBuilder()
    
    for product in products:
        builder.add(KeyboardButton(text=product))
    
    builder.add(KeyboardButton(text="👈 Назад"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)
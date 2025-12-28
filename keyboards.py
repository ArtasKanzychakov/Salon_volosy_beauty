"""
KEYBOARDS.PY - Клавиатуры для бота
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
import config

# ==================== ОСНОВНЫЕ КЛАВИАТУРЫ ====================

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="💇‍♀️ Волосы"))
    builder.add(KeyboardButton(text="🧴 Тело"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def back_to_menu_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для возврата в меню"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🏠 Главное меню"))
    return builder.as_markup(resize_keyboard=True)

# ==================== КАТЕГОРИЯ "ТЕЛО" ====================

def body_goals_keyboard() -> ReplyKeyboardMarkup:
    """Цели ухода за телом"""
    builder = ReplyKeyboardBuilder()
    for goal in config.BODY_GOALS:
        builder.add(KeyboardButton(text=goal))
    builder.add(KeyboardButton(text="🏠 Главное меню"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

# ==================== КАТЕГОРИЯ "ВОЛОСЫ" ====================

def hair_type_keyboard() -> ReplyKeyboardMarkup:
    """Тип волос"""
    builder = ReplyKeyboardBuilder()
    for hair_type in config.HAIR_TYPES:
        builder.add(KeyboardButton(text=hair_type))
    builder.add(KeyboardButton(text="🏠 Главное меню"))
    builder.adjust(1)
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
    builder.add(KeyboardButton(text="🏠 Главное меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def scalp_type_keyboard() -> ReplyKeyboardMarkup:
    """Тип кожи головы"""
    builder = ReplyKeyboardBuilder()
    for scalp_type in config.SCALP_TYPES:
        builder.add(KeyboardButton(text=scalp_type))
    builder.add(KeyboardButton(text="🏠 Главное меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def hair_volume_keyboard() -> ReplyKeyboardMarkup:
    """Объем волос"""
    builder = ReplyKeyboardBuilder()
    for volume in config.HAIR_VOLUME:
        builder.add(KeyboardButton(text=volume))
    builder.add(KeyboardButton(text="🏠 Главное меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def hair_color_keyboard(hair_type: str) -> ReplyKeyboardMarkup:
    """Цвет волос (только для окрашенных)"""
    colors = config.HAIR_COLORS.get(hair_type, [])
    builder = ReplyKeyboardBuilder()
    
    for color in colors:
        builder.add(KeyboardButton(text=color))
    
    builder.add(KeyboardButton(text="🏠 Главное меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# ==================== АДМИН-КЛАВИАТУРЫ ====================

def admin_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню админки"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📤 Загрузить фото"))
    builder.add(KeyboardButton(text="🗑 Удалить фото"))
    builder.add(KeyboardButton(text="📊 Статистика"))
    builder.add(KeyboardButton(text="🚪 Выйти из админки"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def admin_category_keyboard() -> ReplyKeyboardMarkup:
    """Выбор категории для админки"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="💇‍♀️ Волосы"))
    builder.add(KeyboardButton(text="🧴 Тело"))
    builder.add(KeyboardButton(text="↩️ Назад в админку"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def admin_products_keyboard(products: list) -> ReplyKeyboardMarkup:
    """Выбор продукта для админки"""
    builder = ReplyKeyboardBuilder()
    
    for product in products:
        builder.add(KeyboardButton(text=product))
    
    builder.add(KeyboardButton(text="↩️ Назад к категориям"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# ==================== INLINE КЛАВИАТУРЫ ====================

def confirm_delete_keyboard(product_key: str) -> InlineKeyboardMarkup:
    """Подтверждение удаления фото"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ Да, удалить",
        callback_data=f"delete_confirm:{product_key}"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="delete_cancel"
    ))
    return builder.as_markup()

def photo_management_keyboard() -> InlineKeyboardMarkup:
    """Управление фото (для статистики)"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🔄 Обновить статистику",
        callback_data="refresh_stats"
    ))
    builder.add(InlineKeyboardButton(
        text="🗑 Очистить все фото",
        callback_data="clear_all_photos"
    ))
    return builder.as_markup()
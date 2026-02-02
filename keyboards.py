"""
KEYBOARDS.PY - Клавиатуры для бота с пагинацией для админки
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
import config
import photo_map

# ==================== ОСНОВНЫЕ КЛАВИАТУРЫ ====================

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
    builder.add(KeyboardButton(text="💇‍♀️ Новая подборка волосЫ"))
    builder.add(KeyboardButton(text="🧴 Новая подборка телО"))
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
    builder.add(KeyboardButton(text="📸 Управление фото"))
    builder.add(KeyboardButton(text="📊 Статистика"))
    builder.add(KeyboardButton(text="🔄 Обновить список"))
    builder.add(KeyboardButton(text="🏠 В главное меню"))
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)

def admin_photos_keyboard() -> ReplyKeyboardMarkup:
    """Меню управления фото"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📋 Список всех фото"))
    builder.add(KeyboardButton(text="📥 Массовая загрузка"))
    builder.add(KeyboardButton(text="❌ Удалить все фото"))
    builder.add(KeyboardButton(text="↩️ Назад в админку"))
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)

def admin_bulk_upload_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для массовой загрузки"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="💇‍♀️ Загрузить ВОЛОСЫ"))
    builder.add(KeyboardButton(text="🧴 Загрузить ТЕЛО"))
    builder.add(KeyboardButton(text="📋 Показать прогресс"))
    builder.add(KeyboardButton(text="↩️ Назад к фото"))
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)

def admin_category_bulk_keyboard() -> InlineKeyboardMarkup:
    """Выбор категории для массовой загрузки (inline)"""
    builder = InlineKeyboardBuilder()
    
    for category_name, subcategories in config.PHOTO_STRUCTURE_ADMIN.items():
        emoji = "💇‍♀️" if "Волосы" in category_name else "🧴"
        # Используем индексы для callback_data
        category_key = "волосы" if "волосы" in category_name.lower() else "тело"
        builder.add(InlineKeyboardButton(
            text=f"{emoji} {category_name}",
            callback_data=f"bulk_category:{category_key}"
        ))
    
    builder.adjust(1)
    return builder.as_markup()

def admin_subcategory_bulk_keyboard(category: str) -> InlineKeyboardMarkup:
    """Выбор подкатегории для массовой загрузки"""
    builder = InlineKeyboardBuilder()
    
    category_key = "волосы" if "волосы" in category.lower() else "тело"
    category_display = "💇‍♀️ Волосы" if category_key == "волосы" else "🧴 Тело"
    subcategories = list(config.PHOTO_STRUCTURE_ADMIN.get(category_display, {}).items())
    
    for i, (subcategory_name, products) in enumerate(subcategories):
        # Используем индекс вместо названия
        builder.add(InlineKeyboardButton(
            text=subcategory_name,
            callback_data=f"bulk_subcategory_idx:{category_key}:{i}"
        ))
    
    builder.row(
        InlineKeyboardButton(
            text="↩️ Назад к категориям", 
            callback_data="bulk_back_to_categories"
        )
    )
    builder.adjust(1)
    return builder.as_markup()

def admin_photos_list_keyboard(page: int = 0, filter_type: str = "all") -> InlineKeyboardMarkup:
    """Клавиатура для списка фото с пагинацией"""
    builder = InlineKeyboardBuilder()
    
    missing_photos = photo_map.get_missing_photos()
    
    # Фильтрация
    if filter_type == "missing":
        photos_to_show = [p for p in missing_photos if p["status"] == "❌ Отсутствует"]
    elif filter_type == "loaded":
        photos_to_show = [p for p in missing_photos if p["status"] == "✅ Загружено"]
    else:
        photos_to_show = missing_photos
    
    # Пагинация
    per_page = config.ADMIN_PHOTOS_PER_PAGE
    start_idx = page * per_page
    end_idx = start_idx + per_page
    total_pages = (len(photos_to_show) + per_page - 1) // per_page
    
    # Кнопки фильтров
    builder.row(
        InlineKeyboardButton(
            text=f"📋 Все ({len(missing_photos)})", 
            callback_data="photos_list:all:0"
        ),
        InlineKeyboardButton(
            text=f"✅ Загружены ({sum(1 for p in missing_photos if p['status'] == '✅ Загружено')})", 
            callback_data="photos_list:loaded:0"
        ),
        InlineKeyboardButton(
            text=f"❌ Отсутствуют ({sum(1 for p in missing_photos if p['status'] == '❌ Отсутствует')})", 
            callback_data="photos_list:missing:0"
        ),
        width=3
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔄 Обновить", 
            callback_data=f"photos_list:{filter_type}:{page}"
        )
    )
    
    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад", 
            callback_data=f"photos_list:{filter_type}:{page-1}"
        ))
    
    nav_buttons.append(InlineKeyboardButton(
        text=f"{page+1}/{total_pages}", 
        callback_data="no_action"
    ))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ➡️", 
            callback_data=f"photos_list:{filter_type}:{page+1}"
        ))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(text="📥 Массовая загрузка", callback_data="bulk_upload_start"),
        InlineKeyboardButton(text="🏠 В админку", callback_data="admin_back_to_main")
    )
    
    return builder.as_markup()

def admin_confirm_reset_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение удаления всех фото"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ ДА, удалить все", 
        callback_data="confirm_reset_photos"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ НЕТ, отменить", 
        callback_data="cancel_reset_photos"
    ))
    builder.adjust(2)
    return builder.as_markup()

def admin_back_to_photos_keyboard() -> ReplyKeyboardMarkup:
    """Назад к управлению фото"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="↩️ Назад к фото"))
    builder.add(KeyboardButton(text="🏠 В главное меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# ==================== КЛАВИАТУРЫ ДЛЯ ОБЫЧНЫХ ПОЛЬЗОВАТЕЛЕЙ ====================

def help_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для помощи"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="💇‍♀️ Волосы"))
    builder.add(KeyboardButton(text="🧴 Тело"))
    builder.add(KeyboardButton(text="📞 Контакты"))
    builder.add(KeyboardButton(text="💇‍♀️ Новая подборка волосЫ"))
    builder.add(KeyboardButton(text="🧴 Новая подборка телО"))
    builder.add(KeyboardButton(text="🏠 В главное меню"))
    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)

def contacts_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с контактами"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📍 Точки продаж"))
    builder.add(KeyboardButton(text="🚚 Доставка"))
    builder.add(KeyboardButton(text="💬 Написать менеджеру"))
    builder.add(KeyboardButton(text="🏠 В главное меню"))
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)

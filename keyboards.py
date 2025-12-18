from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu():
    """Главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧴 Уход за телом")],
            [KeyboardButton(text="💇‍♀️ Уход за волосами")]
        ],
        resize_keyboard=True
    )

def get_body_menu():
    """Меню для тела"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Общий уход и увлажнение")],
            [KeyboardButton(text="Сухая кожа")],
            [KeyboardButton(text="Чувствительная кожа")],
            [KeyboardButton(text="Борьба с целлюлитом")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )

def get_hair_type_menu():
    """Выбор типа волос"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👱‍♀️ Я блондинка")],
            [KeyboardButton(text="🎨 Окрашенные (шатен/русая/рыжая)")],
            [KeyboardButton(text="🌿 Натуральные волосы")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )

def get_final_menu():
    """Меню после рекомендации"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Новый подбор")],
            [KeyboardButton(text="📍 Точки продаж"), KeyboardButton(text="🚚 Заказать доставку")]
        ],
        resize_keyboard=True
    )
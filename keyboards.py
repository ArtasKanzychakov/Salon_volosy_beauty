from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🧴 Тело"),
                KeyboardButton(text="💇 Волосы")
            ],
            [
                KeyboardButton(text="📍 Точки"),
                KeyboardButton(text="🚚 Доставка")
            ]
        ],
        resize_keyboard=True
    )
    return kb

def get_body_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Общий уход"),
                KeyboardButton(text="Сухая кожа")
            ],
            [
                KeyboardButton(text="Чувствительная"),
                KeyboardButton(text="Целлюлит")
            ],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )
    return kb

def get_hair_type_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👱‍♀️ Блондинки (окрашенные)")],
            [KeyboardButton(text="🎨 Окрашенные волосы")],
            [KeyboardButton(text="🌿 Натуральные волосы")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )
    return kb

def get_hair_color_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Шатенка/Русая")],
            [KeyboardButton(text="Рыжая")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )
    return kb

def get_hair_care_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧴 Общий уход")],
            [KeyboardButton(text="🧴 Общий уход + особенности")],
            [KeyboardButton(text="⚡ Специфические проблемы")],
            [KeyboardButton(text="❤️ Чувствительная кожа головы")],
            [KeyboardButton(text="💨 Объем")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )
    return kb

def get_hair_problems_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Ломкость"),
                KeyboardButton(text="Выпадение")
            ],
            [
                KeyboardButton(text="Перхоть/зуд"),
                KeyboardButton(text="Секущиеся кончики")
            ],
            [
                KeyboardButton(text="Тусклость"),
                KeyboardButton(text="Пушистость")
            ],
            [
                KeyboardButton(text="Тонкие"),
                KeyboardButton(text="Очень поврежденные")
            ],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )
    return kb

def get_hair_additional_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Сухость"),
                KeyboardButton(text="Тонкие волосы")
            ],
            [
                KeyboardButton(text="Пушистость"),
                KeyboardButton(text="Тусклость")
            ],
            [KeyboardButton(text="✅ Готово")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )
    return kb

def get_final_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔄 Новый подбор"),
                KeyboardButton(text="📍 Точки")
            ],
            [KeyboardButton(text="🚚 Доставка")]
        ],
        resize_keyboard=True
    )
    return kb
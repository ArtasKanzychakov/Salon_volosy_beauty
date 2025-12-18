from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton
)

# Главное меню
def get_main_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧴 Уход за телом"), KeyboardButton(text="💇‍♀️ Уход за волосами")]
        ],
        resize_keyboard=True,
        row_width=2
    )
    return kb

# Меню для тела
def get_body_care_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Общий уход и увлажнение")],
            [KeyboardButton(text="Сухая кожа")],
            [KeyboardButton(text="Чувствительная кожа")],
            [KeyboardButton(text="Борьба с целлюлитом")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True,
        row_width=1
    )
    return kb

# Тип волос
def get_hair_type_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👱‍♀️ Я блондинка")],
            [KeyboardButton(text="🎨 Окрашенные (другой цвет)")],
            [KeyboardButton(text="🌿 Натуральные волосы")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True,
        row_width=1
    )
    return kb

# Проблемы волос
def get_problems_inline_keyboard(selected=None):
    if selected is None:
        selected = []
    
    problems = [
        ("Ломкость", "brittle"),
        ("Выпадение", "hair_loss"),
        ("Перхоть", "dandruff"),
        ("Кончики", "split_ends"),
        ("Тусклость", "dull"),
        ("Пушистость", "frizzy"),
        ("Тонкие", "thin"),
        ("Поврежденные", "damaged"),
        ("Нет проблем", "none")
    ]
    
    buttons = []
    for text, code in problems:
        if code in selected:
            buttons.append(InlineKeyboardButton(text=f"✅ {text}", callback_data=f"prob_{code}"))
        else:
            buttons.append(InlineKeyboardButton(text=text, callback_data=f"prob_{code}"))
    
    # Распределяем по 2 кнопки в ряд
    rows = []
    for i in range(0, len(buttons), 2):
        rows.append(buttons[i:i+2])
    
    rows.append([InlineKeyboardButton(text="👍 Готово", callback_data="done")])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

# Да/Нет
def get_yes_no_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True,
        row_width=2
    )
    return kb

# Объем
def get_volume_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да, хочу объем"), KeyboardButton(text="Нет, не нужно")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True,
        row_width=2
    )
    return kb

# Цвет волос
def get_hair_color_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Шатенка"), KeyboardButton(text="Русая")],
            [KeyboardButton(text="Рыжая"), KeyboardButton(text="Другой")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True,
        row_width=2
    )
    return kb

# Финальное меню
def get_final_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Новый подбор")],
            [KeyboardButton(text="📍 Точки продаж"), KeyboardButton(text="🚚 Заказать доставку")]
        ],
        resize_keyboard=True,
        row_width=2
    )
    return kb
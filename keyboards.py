from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("🧴 Уход за телом"), KeyboardButton("💇‍♀️ Уход за волосами"))
    return kb

def back_button():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("◀️ Назад"))
    return kb

def restart_button():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔄 Начать заново"))
    return kb

def body_care():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add(
        KeyboardButton("Общий уход и увлажнение"),
        KeyboardButton("Сухая кожа"),
        KeyboardButton("Чувствительная кожа"),
        KeyboardButton("Борьба с целлюлитом"),
        KeyboardButton("◀️ Назад")
    )
    return kb

def hair_type():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add(
        KeyboardButton("👱‍♀️ Я блондинка"),
        KeyboardButton("🎨 Окрашенные (другой цвет)"),
        KeyboardButton("🌿 Натуральные волосы"),
        KeyboardButton("◀️ Назад")
    )
    return kb

def problems_keyboard(selected=None):
    if selected is None:
        selected = []
    
    kb = InlineKeyboardMarkup(row_width=2)
    
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
    
    for text, code in problems:
        if code in selected:
            kb.insert(InlineKeyboardButton(f"✅ {text}", callback_data=f"prob_{code}"))
        else:
            kb.insert(InlineKeyboardButton(text, callback_data=f"prob_{code}"))
    
    kb.add(InlineKeyboardButton("👍 Готово", callback_data="done"))
    return kb

def yes_no():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("Да"), KeyboardButton("Нет"), KeyboardButton("◀️ Назад"))
    return kb

def volume():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("Да, хочу объем"), KeyboardButton("Нет, не нужно"), KeyboardButton("◀️ Назад"))
    return kb

def hair_color():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("Шатенка"),
        KeyboardButton("Русая"),
        KeyboardButton("Рыжая"),
        KeyboardButton("Другой"),
        KeyboardButton("◀️ Назад")
    )
    return kb

def final_actions():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("🔄 Новый подбор"),
        KeyboardButton("📍 Точки продаж"),
        KeyboardButton("🚚 Заказать доставку")
    )
    return kb
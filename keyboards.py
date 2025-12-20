from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("🧴 Тело"), KeyboardButton("💇 Волосы"))
    kb.row(KeyboardButton("📍 Точки"), KeyboardButton("🚚 Доставка"))
    return kb

def get_body_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("Общий уход"), KeyboardButton("Сухая кожа"))
    kb.row(KeyboardButton("Чувствительная"), KeyboardButton("Целлюлит"))
    kb.add(KeyboardButton("◀️ Назад"))
    return kb

def get_hair_type_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("👱‍♀️ Блондинки (окрашенные)"))
    kb.add(KeyboardButton("🎨 Окрашенные волосы"))
    kb.add(KeyboardButton("🌿 Натуральные волосы"))
    kb.add(KeyboardButton("◀️ Назад"))
    return kb

def get_hair_color_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Шатенка/Русая"))
    kb.add(KeyboardButton("Рыжая"))
    kb.add(KeyboardButton("◀️ Назад"))
    return kb

def get_hair_care_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🧴 Общий уход"))
    kb.add(KeyboardButton("⚡ Специфические проблемы"))
    kb.add(KeyboardButton("❤️ Чувствительная кожа головы"))
    kb.add(KeyboardButton("💨 Объем"))
    kb.add(KeyboardButton("◀️ Назад"))
    return kb

def get_hair_problems_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("Ломкость"), KeyboardButton("Выпадение"))
    kb.row(KeyboardButton("Перхоть/зуд"), KeyboardButton("Секущиеся кончики"))
    kb.row(KeyboardButton("Тусклость"), KeyboardButton("Пушистость"))
    kb.row(KeyboardButton("Тонкие"), KeyboardButton("Очень поврежденные"))
    kb.add(KeyboardButton("◀️ Назад"))
    return kb

def get_final_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("🔄 Новый подбор"), KeyboardButton("📍 Точки"))
    kb.add(KeyboardButton("🚚 Доставка"))
    return kb
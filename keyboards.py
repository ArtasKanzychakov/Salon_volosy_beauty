from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню
def get_main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton(f"{EMOJI['body']} Уход за телом"),
        KeyboardButton(f"{EMOJI['hair']} Уход за волосами")
    )
    return keyboard

# Кнопка назад
def get_back_button():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(f"{EMOJI['back']} Назад"))
    return keyboard

# Кнопка начать заново
def get_restart_button():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(f"{EMOJI['restart']} Начать заново"))
    return keyboard

# Уход за телом
def get_body_care_keyboard(step=None, total_steps=None):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    progress = f" [{step}/{total_steps}]" if step and total_steps else ""
    
    keyboard.add(
        KeyboardButton(f"🧴 Общий уход и увлажнение{progress}"),
        KeyboardButton(f"🌵 Сухая кожа{progress}"),
        KeyboardButton(f"😌 Чувствительная кожа{progress}"),
        KeyboardButton(f"🍑 Борьба с целлюлитом{progress}")
    )
    keyboard.add(KeyboardButton(f"{EMOJI['back']} Назад"))
    return keyboard

# Тип волос
def get_hair_type_keyboard(step=None, total_steps=None):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    progress = f" [{step}/{total_steps}]" if step and total_steps else ""
    
    keyboard.add(
        KeyboardButton(f"👱‍♀️ Да, я блондинка{progress}"),
        KeyboardButton(f"🎨 Да, другой цвет{progress}"),
        KeyboardButton(f"🌿 Нет, волосы натуральные{progress}")
    )
    keyboard.add(KeyboardButton(f"{EMOJI['back']} Назад"))
    return keyboard

# Проблемы волос (мультивыбор через инлайн)
def get_hair_problems_inline_keyboard(selected_problems=None):
    if selected_problems is None:
        selected_problems = []
    
    problems = [
        ("Ломкость", "brittle"),
        ("Выпадение", "hair_loss"),
        ("Перхоть/зуд", "dandruff"),
        ("Секущиеся кончики", "split_ends"),
        ("Тусклость", "dull"),
        ("Пушистость", "frizzy"),
        ("Тонкие и лишённые объёма", "thin"),
        ("Очень повреждённые", "damaged"),
        ("Ничего из перечисленного", "none")
    ]
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    for text, callback in problems:
        if callback in selected_problems:
            text = f"✅ {text}"
        else:
            text = f"◻ {text}"
        keyboard.insert(InlineKeyboardButton(text, callback_data=f"problem_{callback}"))
    
    keyboard.add(InlineKeyboardButton("👍 Готово", callback_data="problems_done"))
    return keyboard

# Кожа головы
def get_scalp_keyboard(step=None, total_steps=None):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    progress = f" [{step}/{total_steps}]" if step and total_steps else ""
    
    keyboard.add(
        KeyboardButton(f"Да{progress}"),
        KeyboardButton(f"Нет{progress}")
    )
    keyboard.add(KeyboardButton(f"{EMOJI['back']} Назад"))
    return keyboard

# Объём
def get_volume_keyboard(step=None, total_steps=None):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    progress = f" [{step}/{total_steps}]" if step and total_steps else ""
    
    keyboard.add(
        KeyboardButton(f"Да, хочу объём{progress}"),
        KeyboardButton(f"Нет, не нужно{progress}")
    )
    keyboard.add(KeyboardButton(f"{EMOJI['back']} Назад"))
    return keyboard

# Цвет волос для окрашенных
def get_hair_color_keyboard(step=None, total_steps=None):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    progress = f" [{step}/{total_steps}]" if step and total_steps else ""
    
    keyboard.add(
        KeyboardButton(f"Шатенка{progress}"),
        KeyboardButton(f"Русая{progress}"),
        KeyboardButton(f"Рыжая{progress}"),
        KeyboardButton(f"Другой цвет{progress}")
    )
    keyboard.add(KeyboardButton(f"{EMOJI['back']} Назад"))
    return keyboard

# Итоговые действия
def get_final_actions_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton(f"{EMOJI['restart']} Новый подбор"),
        KeyboardButton(f"{EMOJI['location']} Точки продаж"),
        KeyboardButton(f"{EMOJI['delivery']} Заказать доставку")
    )
    return keyboard

# Импорт EMOJI из config
from config import EMOJI
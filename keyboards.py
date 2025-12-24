# keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ========== ГЛАВНОЕ МЕНЮ ==========
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧴 Тело"), KeyboardButton(text="💇 Волосы")]
        ],
        resize_keyboard=True
    )

def get_final_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Новый подбор")],
            [KeyboardButton(text="📍 Точки"), KeyboardButton(text="🚚 Доставка")]
        ],
        resize_keyboard=True
    )

# ========== ТЕЛО ==========
def get_body_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Общий уход и увлажнение")],
            [KeyboardButton(text="Сухая кожа")],
            [KeyboardButton(text="Чувствительная и склонная к раздражениям")],
            [KeyboardButton(text="Борьба с целлюлитом и тонизирование")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )

# ========== ВОЛОСЫ ==========
def get_hair_type_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да, я блондинка")],
            [KeyboardButton(text="Да, у меня другой цвет (шатенка, русая, рыжая)")],
            [KeyboardButton(text="Нет, волосы натуральные")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )

def get_hair_problems_menu(selected_problems=None):
    """Клавиатура для выбора проблем (можно несколько)"""
    if selected_problems is None:
        selected_problems = []

    buttons = []
    row = []

    problems = [
        "Ломкость",
        "Выпадение",
        "Перхоть/зуд",
        "Секущиеся кончики",
        "Тусклость",
        "Пушистость",
        "Тонкие и лишенные объема",
        "Очень поврежденные",
        "Ничего из перечисленного, только общий уход"
    ]

    for i, problem in enumerate(problems):
        # Добавляем галочку, если проблема уже выбрана
        display_text = problem
        if problem in selected_problems:
            display_text = f"✅ {problem}"

        row.append(KeyboardButton(text=display_text))

        if len(row) == 2 or i == len(problems) - 1:
            buttons.append(row)
            row = []

    # Кнопка продолжения
    buttons.append([KeyboardButton(text="➡️ Продолжить")])
    buttons.append([KeyboardButton(text="◀️ Назад")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_yes_no_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )

def get_hair_color_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Шатенка")],
            [KeyboardButton(text="Русая")],
            [KeyboardButton(text="Рыжая")],
            [KeyboardButton(text="Другой окрашенный цвет")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )

# ========== АДМИН-ПАНЕЛЬ ==========
def get_admin_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📤 Загрузить фото")],
            [KeyboardButton(text="🗑 Удалить фото")],
            [KeyboardButton(text="📊 Статус фото")],
            [KeyboardButton(text="🔙 Выйти из админки")]
        ],
        resize_keyboard=True
    )

def get_photo_categories_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧴 Тело")],
            [KeyboardButton(text="💇 Волосы - общие")],
            [KeyboardButton(text="👱‍♀️ Блондинки")],
            [KeyboardButton(text="🎨 Окрашенные")],
            [KeyboardButton(text="🎨 Оттеночные маски")],
            [KeyboardButton(text="🖼 Коллажи")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

def get_body_photos_menu():
    """Клавиатура для выбора фото продуктов тела"""
    buttons = [
        [KeyboardButton(text="Молочко для тела")],
        [KeyboardButton(text="Гидрофильное масло")],
        [KeyboardButton(text="Крем-суфле")],
        [KeyboardButton(text="Скраб кофе/кокос")],
        [KeyboardButton(text="Гель для душа (вишня/манго/лимон)")],
        [KeyboardButton(text="Баттер для тела")],
        [KeyboardButton(text="Гиалуроновая кислота для лица")],  # ← ДОБАВЛЕНО
        [KeyboardButton(text="Антицеллюлитный скраб (мята)")],
        [KeyboardButton(text="🔙 К категориям")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_hair_common_menu():
    buttons = [
        [KeyboardButton(text="Биолипидный спрей")],
        [KeyboardButton(text="Сухое масло спрей")],
        [KeyboardButton(text="Масло ELIXIR")],
        [KeyboardButton(text="Молочко для волос")],
        [KeyboardButton(text="Масло-концентрат")],
        [KeyboardButton(text="Флюид для волос")],
        [KeyboardButton(text="Шампунь реконстракт")],
        [KeyboardButton(text="Маска реконстракт")],
        [KeyboardButton(text="Протеиновый крем")],
        [KeyboardButton(text="🔙 К категориям")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_blonde_photos_menu():
    buttons = [
        [KeyboardButton(text="Шампунь для осветленных волос с гиалуроновой кислотой")],
        [KeyboardButton(text="Кондиционер для осветленных волос с гиалуроновой кислотой")],
        [KeyboardButton(text="Маска для осветленных волос с гиалуроновой кислотой")],
        [KeyboardButton(text="🔙 К категориям")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_colored_photos_menu():
    buttons = [
        [KeyboardButton(text="Шампунь для окрашенных волос с коллагеном")],
        [KeyboardButton(text="Кондиционер для окрашенных волос с коллагеном")],
        [KeyboardButton(text="Маска для окрашенных волос с коллагеном")],
        [KeyboardButton(text="🔙 К категориям")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_tone_masks_menu():
    buttons = [
        [KeyboardButton(text="Оттеночная маска Холодный шоколад")],
        [KeyboardButton(text="Оттеночная маска Медный")],
        [KeyboardButton(text="🔙 К категориям")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_collage_menu():
    buttons = [
        [KeyboardButton(text="Коллаж для тела")],
        [KeyboardButton(text="Коллаж для блондинок")],
        [KeyboardButton(text="Коллаж: Окрашенные волосы")],
        [KeyboardButton(text="Коллаж: Натуральные волосы")],
        [KeyboardButton(text="Коллаж: Ломкость волос")],
        [KeyboardButton(text="Коллаж: Тусклость")],
        [KeyboardButton(text="Коллаж: Пушистость")],
        [KeyboardButton(text="Коллаж: Тонкие волосы")],
        [KeyboardButton(text="Коллаж: Поврежденные волосы")],
        [KeyboardButton(text="Коллаж: Объем")],
        [KeyboardButton(text="Коллаж: Чувствительная кожа головы")],
        [KeyboardButton(text="Коллаж: Выпадение волос")],
        [KeyboardButton(text="Коллаж: Перхоть/зуд")],
        [KeyboardButton(text="🔙 К категориям")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_delete_confirmation():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да, удалить")],
            [KeyboardButton(text="❌ Нет, отмена")]
        ],
        resize_keyboard=True
    )
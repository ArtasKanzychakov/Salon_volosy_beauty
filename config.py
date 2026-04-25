"""
CONFIG.PY - Конфигурация для бота с массовой загрузкой фото
ОБНОВЛЕНО: добавлены новые ключи фото, исправлен PHOTO_MAPPING
"""

import os
from typing import List

# ==================== БАЗОВЫЕ НАСТРОЙКИ ====================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    print("⚠️ ВНИМАНИЕ: BOT_TOKEN не найден в переменных окружения!")

ADMIN_PASSWORD = "admin2026"
ADMIN_PHOTOS_PER_PAGE = 5

# ==================== ДАННЫЕ ДЛЯ РЕКОМЕНДАЦИЙ ====================

BODY_GOALS = [
    "Общий уход и увлажнение",
    "Сухая кожа",
    "Чувствительная и склонная к раздражениям",
    "Борьба с целлюлитом и тонизирование"
]

HAIR_TYPES = [
    "Окрашенные блондинки",
    "Окрашенные",
    "Натуральные"
]

HAIR_PROBLEMS = [
    "Ломкость",
    "Выпадение",
    "Перхоть/зуд",
    "Секущиеся кончики",
    "Тусклость",
    "Пушистость",
    "Тонкие",
    "Очень поврежденные"
]

SCALP_TYPES = ["Да, чувствительная", "Нет"]
HAIR_VOLUME = ["Да, хочу объем", "Нет, не нужно"]

def get_hair_colors(hair_type: str):
    if hair_type == "Окрашенные":
        return ["Брюнетка", "Шатенка", "Русая", "Рыжая"]
    return []

# ==================== СТРУКТУРА ПРОДУКТОВ ДЛЯ АДМИНКИ ====================

PHOTO_STRUCTURE_ADMIN = {
    "💇‍♀️ Волосы": {
        "👱‍♀️ Для блондинок": [
            ("blonde_shampoo",       "Шампунь для блондинок"),
            ("blonde_conditioner",   "Кондиционер для блондинок"),
            ("blonde_mask",          "Маска для блондинок"),
            ("dry_oil_spray",        "Сухое масло спрей"),
            ("mask_pink_powder",     "Маска розовая пудра"),
            ("mask_mother_of_pearl", "Маска перламутр"),
        ],
        "🎨 Для окрашенных волос": [
            ("colored_shampoo",     "Шампунь для окрашенных волос"),
            ("colored_conditioner", "Кондиционер для окрашенных"),
            ("colored_mask",        "Маска для окрашенных"),
        ],
        "🌿 Для натуральных волос": [
            ("natural_shampoo",     "Шампунь укрепление и сила"),
            ("natural_conditioner", "Кондиционер укрепление и сила"),
            ("strengthening_spray", "Укрепляющий спрей для волос"),
        ],
        "💪 Укрепление и восстановление": [
            ("strengthening_mask",  "Укрепляющая маска для волос"),
            ("biolipid_spray",      "Биолипидный спрей"),
            ("protein_cream",       "Протеиновый крем"),
            ("reconstruct_shampoo", "Шампунь реконстракт"),
            ("reconstruct_mask",    "Маска реконстракт"),
        ],
        "📈 Для тонких волос": [
            ("thin_hair_shampoo",    "Шампунь для тонких волос"),
            ("thin_hair_conditioner","Кондиционер для тонких волос"),
        ],
        "✨ Масла, флюиды, молочко": [
            ("oil_elixir",      "Масло ELIXIR"),
            ("oil_concentrate", "Масло-концентрат"),
            ("hair_fluid",      "Флюид для волос"),
            ("hair_milk",       "Молочко для волос"),
        ],
        "🩺 Лечебный уход": [
            ("anti_loss_shampoo",       "Шампунь против выпадения"),
            ("hair_growth_lotion",      "Лосьон стимулирующий рост волос"),
            ("anti_dandruff_shampoo",   "Шампунь против перхоти"),
            ("sensitive_scalp_shampoo", "Шампунь для чувствительной кожи головы"),
        ],
        "🎨 Оттеночные маски": [
            ("mask_cold_chocolate",  "Маска холодный шоколад"),
            ("mask_copper",          "Маска медный"),
            ("mask_pink_powder",     "Маска розовая пудра"),
            ("mask_mother_of_pearl", "Маска перламутр"),
        ],
        "👨 Для мужчин": [
            ("men_shampoo", "Шампунь для мужчин"),
        ],
    },
    "🧴 Тело": {
        "🧴 Кремы и масла": [
            ("cream_body",      "Крем суфле для тела"),
            ("hydrophilic_oil", "Гидрофильное масло"),
            ("body_butter",     "Баттер для тела"),
            ("body_milk",       "Молочко для тела"),
            ("hualuronic_acid", "Гиалуроновая кислота"),
        ],
        "🚿 Очищение и скрабы": [
            ("body_scrub",    "Скраб для тела"),
            ("shower_gel",    "Гель для душа"),
            ("perfumed_soap", "Парфюмерное мыло"),
        ],
    }
}

# ==================== МАППИНГ ФОТО ДЛЯ РЕКОМЕНДАЦИЙ ====================
# Порядок ключей = порядок отправки фото пользователю.
# Ключи без загруженного фото пропускаются автоматически.

PHOTO_MAPPING = {
    "тело": {
        "Общий уход и увлажнение": [
            "body_milk",
            "hydrophilic_oil",
            "cream_body",
            "body_scrub",
            "shower_gel",
            "hualuronic_acid",
        ],
        "Сухая кожа": [
            "hydrophilic_oil",
            "body_butter",
            "hualuronic_acid",
        ],
        "Чувствительная и склонная к раздражениям": [
            "shower_gel",
            "body_milk",
            "hydrophilic_oil",
            "hualuronic_acid",
        ],
        "Борьба с целлюлитом и тонизирование": [
            "shower_gel",
            "body_scrub",
            "body_milk",
            "hualuronic_acid",
        ],
    },
    "волосы": {
        # ── Базовый уход по типу волос ──────────────────────────────────
        "Окрашенные блондинки": [
            "blonde_shampoo",
            "blonde_conditioner",
            "blonde_mask",
            "biolipid_spray",
            "hair_milk",
        ],
        "Окрашенные": [
            "colored_shampoo",
            "colored_conditioner",
            "colored_mask",
            "biolipid_spray",
            "protein_cream",
        ],
        "Натуральные": [
            "natural_shampoo",
            "natural_conditioner",
            "strengthening_mask",
            "biolipid_spray",
            "strengthening_spray",
            "protein_cream",
        ],

        # ── Проблемы ────────────────────────────────────────────────────
        "Ломкость": [
            "biolipid_spray",
            "hair_fluid",
            "oil_elixir",
            "protein_cream",
            "strengthening_spray",
            "strengthening_mask",
        ],
        "Выпадение": [
            "anti_loss_shampoo",
            "hair_growth_lotion",
        ],
        "Перхоть/зуд": [
            "anti_dandruff_shampoo",
        ],
        "Секущиеся кончики": [
            "oil_elixir",
        ],
        "Тусклость": [
            "hair_milk",
            "oil_concentrate",
            "dry_oil_spray",
        ],
        "Пушистость": [
            "hair_fluid",
            "protein_cream",
            "oil_elixir",
            "hair_milk",
        ],
        "Тонкие": [
            "thin_hair_shampoo",
            "thin_hair_conditioner",
            "strengthening_mask",
            "strengthening_spray",
        ],
        "Очень поврежденные": [
            "reconstruct_shampoo",
            "reconstruct_mask",
            "biolipid_spray",
            "hair_fluid",
            "oil_elixir",
        ],

        # ── Дополнительные опции ────────────────────────────────────────
        "чувствительная_кожа": [
            "sensitive_scalp_shampoo",
        ],
        "объем": [
            "thin_hair_shampoo",
            "thin_hair_conditioner",
            "strengthening_spray",
            "strengthening_mask",
        ],

        # ── Оттеночные маски ────────────────────────────────────────────
        "оттеночная_шоколад": [
            "mask_cold_chocolate",
        ],
        "оттеночная_медный": [
            "mask_copper",
        ],
    }
}

# ==================== ДАННЫЕ ДЛЯ РЕКОМЕНДАЦИЙ (ТЕКСТ) ====================

BODY_DATA = {
    "Общий уход и увлажнение": {
        "title": "🧴 <b>Рекомендация для общего ухода и увлажнения:</b>",
        "products": [
            "Молочко для тела",
            "Гидрофильное масло",
            "Крем-суфле",
            "Скраб кофе/кокос",
            "Гель для душа (вишня/манго/лимон)"
        ],
        "note": "+ Гиалуроновая кислота для лица"
    },
    "Сухая кожа": {
        "title": "🌵 <b>Рекомендация для сухой кожи:</b>",
        "products": [
            "Гидрофильное масло",
            "Баттер для тела"
        ],
        "note": "+ Гиалуроновая кислота для лица"
    },
    "Чувствительная и склонная к раздражениям": {
        "title": "😌 <b>Рекомендация для чувствительной кожи:</b>",
        "products": [
            "Гель для душа (вишня/манго/лимон)",
            "Молочко для тела",
            "Гидрофильное масло"
        ],
        "note": "+ Гиалуроновая кислота для лица"
    },
    "Борьба с целлюлитом и тонизирование": {
        "title": "🍑 <b>Рекомендация для борьбы с целлюлитом:</b>",
        "products": [
            "Гель для душа (вишня/манго/лимон)",
            "Антицеллюлитный скраб (мята)",
            "Молочко для тела"
        ],
        "note": "+ Гиалуроновая кислота для лица"
    }
}

# ==================== ФУНКЦИИ ДЛЯ РЕКОМЕНДАЦИЙ ====================

def get_body_recommendations_html(goal: str) -> str:
    if goal in BODY_DATA:
        data = BODY_DATA[goal]
        text = f"{data['title']}\n\n"
        for product in data['products']:
            text += f"• {product}\n"
        if 'note' in data:
            text += f"\n{data['note']}"
        return text
    return "Рекомендации временно недоступны."

def get_hair_recommendations_html(hair_type: str, problems: list, scalp_type: str,
                                  hair_volume: str, hair_color: str = "") -> str:
    result = "💇‍♀️ <b>Персонализированный уход для ваших волос:</b>\n\n"

    if hair_type == "Окрашенные блондинки":
        result += "<b>Базовый уход для блондинок:</b>\n"
        result += "• Шампунь для осветленных волос с гиалуроновой кислотой\n"
        result += "• Кондиционер для осветленных волос с гиалуроновой кислотой\n"
        result += "• Маска для осветленных волос с гиалуроновой кислотой\n"
        result += "• Биолипидный спрей\n"
        result += "• Молочко для волос\n\n"
    elif hair_type == "Окрашенные":
        result += "<b>Базовый уход для окрашенных волос:</b>\n"
        result += "• Шампунь для окрашенных волос с коллагеном\n"
        result += "• Кондиционер для окрашенных волос с коллагеном\n"
        result += "• Маска для окрашенных волос с коллагеном\n"
        result += "• Биолипидный спрей\n"
        result += "• Протеиновый крем для волос\n\n"
    else:
        result += "<b>Базовый уход для натуральных волос:</b>\n"
        result += "• Шампунь укрепление и сила\n"
        result += "• Кондиционер укрепление и сила\n"
        result += "• Укрепляющая маска для волос\n"
        result += "• Биолипидный спрей\n"
        result += "• Укрепляющий спрей для волос\n"
        result += "• Протеиновый крем\n\n"

    if problems:
        result += "<b>Дополнительный уход для выбранных проблем:</b>\n"

        problem_solutions = {
            "Ломкость": (
                "• Биолипидный спрей\n"
                "• Флюид для волос\n"
                "• Масло ELIXIR\n"
                "• Протеиновый крем\n"
                "• Укрепляющий спрей для волос\n"
                "• Укрепляющая маска для волос\n"
            ),
            "Выпадение": (
                "• Шампунь против выпадения\n"
                "• Лосьон стимулирующий рост волос\n"
            ),
            "Перхоть/зуд": (
                "• Шампунь против перхоти\n"
            ),
            "Секущиеся кончики": (
                "• Масло ELIXIR\n"
            ),
            "Тусклость": (
                "• Молочко для волос\n"
                "• Масло-концентрат\n"
                "• Сухое масло спрей\n"
            ),
            "Пушистость": (
                "• Флюид для волос\n"
                "• Протеиновый крем\n"
                "• Масло ELIXIR\n"
                "• Молочко для волос\n"
            ),
            "Тонкие": (
                "• Шампунь для тонких волос\n"
                "• Кондиционер для тонких волос\n"
                "• Укрепляющая маска для волос\n"
                "• Укрепляющий спрей для волос\n"
            ),
            "Очень поврежденные": (
                "• Шампунь реконстракт\n"
                "• Маска реконстракт\n"
                "• Биолипидный спрей\n"
                "• Флюид для волос\n"
                "• Масло ELIXIR\n"
            ),
        }

        for problem in problems:
            if problem in problem_solutions:
                result += f"\n<b>{problem}:</b>\n{problem_solutions[problem]}"

    if scalp_type == "Да, чувствительная":
        result += "\n<b>Для чувствительной кожи головы:</b>\n"
        result += "• Шампунь для чувствительной кожи головы\n"

    if hair_volume == "Да, хочу объем":
        result += "\n<b>Для объема волос:</b>\n"
        result += "• Шампунь для тонких волос укрепление и сила\n"
        result += "• Кондиционер для тонких волос укрепление и сила\n"
        result += "• Укрепляющий спрей для волос\n"
        result += "• Укрепляющая маска для волос\n"

    if hair_type == "Окрашенные":
        if hair_color in ["Шатенка", "Русая"]:
            result += "\n<b>Для поддержания цвета:</b>\n"
            result += "• Оттеночная маска Холодный шоколад\n"
        elif hair_color == "Рыжая":
            result += "\n<b>Для поддержания цвета:</b>\n"
            result += "• Оттеночная маска Медный\n"

    return result

# ==================== ИНФОРМАЦИЯ О ПРОДАЖАХ ====================

SALES_POINTS = (
    "<b>📍 Точки продаж:</b>\n"
    "• Салон красоты COLORIST Лермонтова 21\n"
    "  Без выходных с 9.00 до 20.00\n\n"
    "• Тц Европа 1 этаж отдел ZOOM Box\n"
    "  Без выходных с 10.00 до 21.00\n\n"
    "• Тц Калина 1 этаж отдел Dark point\n"
    "  Без выходных с 10.00 до 21.00"
)

DELIVERY_INFO = (
    "<b>🚚 Доставка:</b>\n"
    "Вы можете заказать доставку выбранных продуктов, "
    "перекинув свой заказ в личку @LARMOSS_cosmetics\n\n"
    "Так же вы можете более подробно познакомиться с нашей продукцией на сайте https://larmoss.ru/"
)

# ==================== ЦЕНЫ ПРОДУКТОВ ====================

PRODUCT_PRICES = {
    # Тело
    "cream_body":       "750₽",
    "hydrophilic_oil":  "700₽",
    "body_butter":      "1000₽",
    "body_milk":        "1000₽",
    "hualuronic_acid":  "700₽ / 1400₽",
    "body_scrub":       "700₽",
    "shower_gel":       "800₽",
    "perfumed_soap":    "600₽",

    # Волосы — базовый уход
    "blonde_shampoo":       "900₽",
    "blonde_conditioner":   "1200₽",
    "blonde_mask":          "1500₽",
    "colored_shampoo":      "900₽",
    "colored_conditioner":  "1200₽",
    "colored_mask":         "1500₽",
    "natural_shampoo":      "900₽",
    "natural_conditioner":  "1200₽",
    "thin_hair_shampoo":    "900₽",
    "thin_hair_conditioner":"1200₽",
    "reconstruct_shampoo":  "900₽",
    "reconstruct_mask":     "1700₽",

    # Лечебный уход
    "anti_loss_shampoo":       "900₽",
    "hair_growth_lotion":      "1200₽",
    "anti_dandruff_shampoo":   "900₽",
    "sensitive_scalp_shampoo": "900₽",

    # Спреи, масла, кремы
    "dry_oil_spray":        "1400₽",
    "biolipid_spray":       "1100₽",
    "protein_cream":        "1100₽",
    "hair_milk":            "1100₽",
    "hair_fluid":           "1300₽",
    "oil_concentrate":      "900₽",
    "oil_elixir":           "1500₽",
    "strengthening_mask":   "1500₽",
    "strengthening_spray":  "1100₽",

    # Оттеночные маски
    "mask_cold_chocolate":  "1700₽",
    "mask_copper":          "1700₽",
    "mask_pink_powder":     "1700₽",
    "mask_mother_of_pearl": "1700₽",

    # Мужская линия
    "men_shampoo":          "800₽",
}

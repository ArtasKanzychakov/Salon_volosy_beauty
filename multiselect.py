# multiselect.py - Мультивыбор проблем для волос

ADDITIONAL_PROBLEMS = {
    "Сухость": {
        "products": ["Глубоко увлажняющая сыворотка", "Увлажняющая маска"],
        "note": "Для дополнительного увлажнения"
    },
    "Тонкие волосы": {
        "products": ["Спрей для объема", "Шампунь для придания объема"],
        "note": "Для увеличения объема"
    },
    "Пушистость": {
        "products": ["Стайлинг-крем", "Масло для гладкости"],
        "note": "Для контроля пушистости"
    },
    "Тусклость": {
        "products": ["Осветляющая сыворотка", "Блеск-спрей"],
        "note": "Для блеска"
    }
}

def format_additional_problems(selected_problems):
    """Форматирует выбранные дополнительные проблемы"""
    if not selected_problems:
        return ""
    
    response = "\n<b>➕ Дополнительные рекомендации:</b>\n"
    
    for problem in selected_problems:
        if problem in ADDITIONAL_PROBLEMS:
            response += f"\n<b>{ADDITIONAL_PROBLEMS[problem]['note']}:</b>\n"
            for product in ADDITIONAL_PROBLEMS[problem]["products"]:
                response += f"• {product}\n"
    
    return response
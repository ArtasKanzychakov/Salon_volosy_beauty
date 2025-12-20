# multiselect.py - Мультивыбор проблем для волос

ADDITIONAL_PROBLEMS = {
    # Проблемы, которые можно добавить к общему уходу
    "Сухость": {
        "products": ["Глубоко увлажняющая сыворотка", "Увлажняющая маска"],
        "note": "Для дополнительного увлажнения:"
    },
    "Тонкие волосы": {
        "products": ["Спрей для объема", "Шампунь для придания объема"],
        "note": "Для увеличения объема:"
    },
    "Пушистость": {
        "products": ["Стайлинг-крем", "Масло для гладкости"],
        "note": "Для контроля пушистости:"
    },
    "Тусклость": {
        "products": ["Осветляющая сыворотка", "Блеск-спрей"],
        "note": "Для блеска:"
    }
}

def combine_recommendations(base_products, selected_problems):
    """Объединяет базовые продукты с дополнительными"""
    result = base_products.copy()
    notes = []
    
    for problem in selected_problems:
        if problem in ADDITIONAL_PROBLEMS:
            result.append(f"\n<b>{ADDITIONAL_PROBLEMS[problem]['note']}</b>")
            for product in ADDITIONAL_PROBLEMS[problem]["products"]:
                result.append(f"• {product}")
    
    return result
"""
PHOTO_MAP.PY - Статическое хранилище file_id фотографий
Это решение выбрано осознанно для работы на Render Free
вместо использования внешних баз данных.
"""

# ==================== СТАТИЧЕСКОЕ ХРАНИЛИЩЕ ФОТОГРАФИЙ ====================
# Правила использования:
# 1. product_key НИКОГДА не меняется
# 2. Меняется ТОЛЬКО file_id
# 3. Для добавления фото используйте /admin команду
# 4. Скопируйте полученный file_id и вставьте сюда

PHOTO_MAP = {
    # ==================== ТЕЛО ====================
    
    # Кремы и масла
    "cream_body": "",
    "hydrophilic_oil": "",
    "body_butter": "",
    "body_milk": "",
    "hualuronic_acid": "",
    
    # Очищение и скрабы
    "body_scrub": "",
    "shower_gel": "",
    
    # ==================== ВОЛОСЫ ====================
    
    # Для блондинок
    "blonde_shampoo": "",
    "blonde_conditioner": "",
    "blonde_mask": "",
    "dry_oil_spray": "",
    "mask_pink_powder": "",
    "mask_mother_of_pearl": "",
    
    # Для окрашенных волос
    "colored_conditioner": "",
    "colored_mask": "",
    
    # Маски и эликсиры
    "oil_elixir": "",
    "oil_concentrate": "",
    "hair_fluid": "",
    
    # Восстановление
    "reconstruct_shampoo": "",
    "reconstruct_mask": "",
    "biolipid_spray": "",
    "protein_cream": "",
    
    # Для ухода
    "hair_milk": "",
    
    # Оттеночные маски
    "mask_cold_chocolate": "",
    "mask_copper": "",
}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_photo_file_id(product_key: str) -> str:
    """Получить file_id для product_key"""
    return PHOTO_MAP.get(product_key, "")

def set_photo_file_id(product_key: str, file_id: str):
    """Установить file_id для product_key (использовать только при обновлении кода)"""
    if product_key in PHOTO_MAP:
        PHOTO_MAP[product_key] = file_id
        return True
    return False

def get_all_photos() -> dict:
    """Получить все фотографии"""
    return {k: v for k, v in PHOTO_MAP.items() if v}

def get_photos_by_keys(photo_keys: list) -> list:
    """Получить список file_id по списку ключей"""
    result = []
    for key in photo_keys:
        if key in PHOTO_MAP and PHOTO_MAP[key]:
            result.append(PHOTO_MAP[key])
    return result
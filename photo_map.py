"""
PHOTO_MAP.PY - Статическое хранилище file_id фотографий
Автоматическое обновление при загрузке через админ-панель
"""

import json
import os
from typing import Dict, List, Optional

# ==================== ПУТЬ К ФАЙЛУ ХРАНЕНИЯ ====================
PHOTO_MAP_FILE = "photo_map_data.json"

# ==================== СТАНДАРТНЫЕ КЛЮЧИ ДЛЯ ВСЕХ ФОТО ====================
ALL_PHOTO_KEYS = {
    # Тело
    "cream_body": "Крем для тела",
    "hydrophilic_oil": "Гидрофильное масло", 
    "body_butter": "Баттер для тела",
    "body_milk": "Молочко для тела",
    "hualuronic_acid": "Гиалуроновая кислота",
    "body_scrub": "Скраб для тела",
    "shower_gel": "Гель для душа",
    
    # Волосы
    "blonde_shampoo": "Шампунь для блондинок",
    "blonde_conditioner": "Кондиционер для блондинок", 
    "blonde_mask": "Маска для блондинок",
    "dry_oil_spray": "Сухое масло спрей",
    "mask_pink_powder": "Маска розовая пудра",
    "mask_mother_of_pearl": "Маска перламутр",
    "colored_conditioner": "Кондиционер для окрашенных",
    "colored_mask": "Маска для окрашенных",
    "oil_elixir": "Масло ELIXIR",
    "oil_concentrate": "Масло концентрат",
    "hair_fluid": "Флюид для волос",
    "reconstruct_shampoo": "Шампунь реконстракт",
    "reconstruct_mask": "Маска реконстракт",
    "biolipid_spray": "Биолипидный спрей",
    "protein_cream": "Протеиновый крем",
    "hair_milk": "Молочко для волос",
    "mask_cold_chocolate": "Маска холодный шоколад",
    "mask_copper": "Маска медный",
}

# ==================== ЗАГРУЗКА И СОХРАНЕНИЕ ДАННЫХ ====================

def load_photo_map() -> Dict[str, str]:
    """Загрузить фото-мап из файла"""
    try:
        if os.path.exists(PHOTO_MAP_FILE):
            with open(PHOTO_MAP_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Ошибка загрузки фото-мапа: {e}")
    
    # Возвращаем пустой словарь, если файла нет или ошибка
    return {}

def save_photo_map(data: Dict[str, str]):
    """Сохранить фото-мап в файл"""
    try:
        with open(PHOTO_MAP_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения фото-мапа: {e}")
        return False

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================

def get_photo_file_id(product_key: str) -> str:
    """Получить file_id для product_key"""
    data = load_photo_map()
    return data.get(product_key, "")

def set_photo_file_id(product_key: str, file_id: str) -> bool:
    """Установить file_id для product_key и сохранить в файл"""
    if product_key not in ALL_PHOTO_KEYS:
        print(f"⚠️ Неизвестный ключ: {product_key}")
        return False
    
    data = load_photo_map()
    data[product_key] = file_id
    return save_photo_map(data)

def get_all_photos() -> Dict[str, str]:
    """Получить все загруженные фотографии"""
    return load_photo_map()

def get_photos_by_keys(photo_keys: List[str]) -> List[str]:
    """Получить список file_id по списку ключей"""
    data = load_photo_map()
    result = []
    for key in photo_keys:
        if key in data and data[key]:
            result.append(data[key])
    return result

def get_missing_photos() -> List[Dict[str, str]]:
    """Получить список отсутствующих фото"""
    data = load_photo_map()
    missing = []
    
    for key, name in ALL_PHOTO_KEYS.items():
        status = "✅ Загружено" if key in data and data[key] else "❌ Отсутствует"
        missing.append({
            "key": key,
            "name": name,
            "status": status,
            "file_id": data.get(key, "")
        })
    
    return missing

def get_photo_stats() -> Dict[str, int]:
    """Получить статистику по фото"""
    data = load_photo_map()
    total = len(ALL_PHOTO_KEYS)
    loaded = sum(1 for key in ALL_PHOTO_KEYS if key in data and data[key])
    
    return {
        "total": total,
        "loaded": loaded,
        "missing": total - loaded,
        "percentage": round((loaded / total) * 100, 1) if total > 0 else 0
    }

def reset_all_photos() -> bool:
    """Сбросить все фото (очистить файл)"""
    return save_photo_map({})

# Инициализируем файл при импорте
if not os.path.exists(PHOTO_MAP_FILE):
    save_photo_map({})
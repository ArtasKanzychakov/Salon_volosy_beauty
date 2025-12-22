# photo_storage.py - Хранилище ID фото из Telegram
import json
import os
from typing import Dict, List, Optional

STORAGE_FILE = "photo_storage.json"

# Базовые соответствия продуктов и их ключей в хранилище
PHOTO_KEYS = {
    # ========== ТЕЛО ==========
    "body_milk": "Молочко для тела",
    "hydrophilic_oil": "Гидрофильное масло",
    "cream_body": "Крем-суфле",
    "body_scrub": "Скраб кофе/кокос",
    "shower_gel": "Гель для душа (вишня/манго/лимон)",
    "body_butter": "Баттер для тела",
    "hyaluronic_acid": "Гиалуроновая кислота для лица",
    "anticellulite_scrub": "Антицеллюлитный скраб (мята)",
    
    # ========== ВОЛОСЫ - ОБЩИЕ ==========
    "biolipid_spray": "Биолипидный спрей",
    "dry_oil_spray": "Сухое масло спрей",
    "oil_elixir": "Масло ELIXIR",
    "hair_milk": "Молочко для волос",
    "oil_concentrate": "Масло-концентрат",
    "hair_fluid": "Флюид для волос",
    "reconstruct_shampoo": "Шампунь реконстракт",
    "reconstruct_mask": "Маска реконстракт",
    "protein_cream": "Протеиновый крем",
    
    # ========== БЛОНДИНКИ ==========
    "blonde_shampoo": "Шампунь для осветленных волос с гиалуроновой кислотой",
    "blonde_conditioner": "Кондиционер для осветленных волос с гиалуроновой кислотой",
    "blonde_mask": "Маска для осветленных волос с гиалуроновой кислотой",
    
    # ========== ОКРАШЕННЫЕ ==========
    "colored_shampoo": "Шампунь для окрашенных волос с коллагеном",
    "colored_conditioner": "Кондиционер для окрашенных волос с коллагеном",
    "colored_mask": "Маска для окрашенных волос с коллагеном",
    
    # ========== ОТТЕНОЧНЫЕ МАСКИ ==========
    "mask_cold_chocolate": "Оттеночная маска Холодный шоколад",
    "mask_copper": "Оттеночная маска Медный",
    
    # ========== КОЛЛАЖИ ==========
    "collage_blonde": "Коллаж для блондинок",
    "collage_colored": "Коллаж: Окрашенные волосы",
    "collage_natural": "Коллаж: Натуральные волосы",
    "collage_lomkost": "Коллаж: Ломкость волос",
    "collage_tusk": "Коллаж: Тусклость",
    "collage_fluffy": "Коллаж: Пушистость",
    "collage_thin": "Коллаж: Тонкие волосы",
    "collage_damaged": "Коллаж: Поврежденные волосы",
    "collage_volume": "Коллаж: Объем",
    "collage_scalp": "Коллаж: Чувствительная кожа головы",
    "collage_loss": "Коллаж: Выпадение волос",
    "collage_dandruff": "Коллаж: Перхоть/зуд"
}

class PhotoStorage:
    def __init__(self):
        self.storage = self._load_storage()
    
    def _load_storage(self) -> Dict:
        """Загрузить хранилище из файла"""
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_storage(self):
        """Сохранить хранилище в файл"""
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.storage, f, ensure_ascii=False, indent=2)
    
    def save_photo_id(self, key: str, file_id: str):
        """Сохранить ID фото для ключа"""
        self.storage[key] = file_id
        self._save_storage()
    
    def get_photo_id(self, key: str) -> Optional[str]:
        """Получить ID фото по ключу"""
        return self.storage.get(key)
    
    def delete_photo(self, key: str):
        """Удалить фото из хранилища"""
        if key in self.storage:
            del self.storage[key]
            self._save_storage()
            return True
        return False
    
    def get_all_photos(self) -> Dict:
        """Получить все сохраненные фото"""
        return self.storage.copy()
    
    def get_missing_photos(self) -> List[str]:
        """Получить список ключей, для которых нет фото"""
        missing = []
        for key in PHOTO_KEYS.keys():
            if key not in self.storage:
                missing.append(key)
        return missing
    
    def get_photo_status(self) -> Dict[str, bool]:
        """Получить статус загрузки всех фото"""
        status = {}
        for key, name in PHOTO_KEYS.items():
            status[name] = key in self.storage
        return status

# Глобальный экземпляр хранилища
photo_storage = PhotoStorage()
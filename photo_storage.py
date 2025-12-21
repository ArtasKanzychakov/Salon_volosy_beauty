# Хранилище ID фото из Telegram (25 фото)
import json
import os

STORAGE_FILE = "photo_storage.json"

# Ключи для 25 фото продуктов
PHOTO_KEYS = {
    # 🧴 ТЕЛО (7 фото)
    "body_milk": "Молочко для тела",
    "hydrophilic_oil": "Гидрофильное масло",
    "cream_body": "Крем суфле",
    "body_scrub": "Скраб для тела",
    "shower_gel": "Гель для душа",
    "body_butter": "Баттер для тела",
    "hyaluronic_acid": "Гиалуроновая кислота",
    
    # 💇 ВОЛОСЫ - ОБЩИЕ (9 фото)
    "biolipid_spray": "Биолипидный спрей",
    "dry_oil_spray": "Сухое масло спрей",
    "oil_elixir": "Масло ELIXIR",
    "hair_milk": "Молочко для волос",
    "oil_concentrate": "Масло концентрат",
    "hair_fluid": "Флюид для волос",
    "reconstruct_shampoo": "Шампунь реконстракт",
    "reconstruct_mask": "Маска реконстракт",
    "protein_cream": "Протеиновый крем",
    
    # 👱‍♀️ БЛОНДИНКИ (3 фото)
    "blonde_shampoo": "Шампунь для осветленных волос",
    "blonde_conditioner": "Кондиционер для осветленных волос",
    "blonde_mask": "Маска для осветленных волос",
    
    # 🎨 ОКРАШЕННЫЕ (3 фото)
    "colored_shampoo": "Шампунь для окрашенных волос",
    "colored_conditioner": "Кондиционер для окрашенных волос",
    "colored_mask": "Маска для окрашенных волос",
    
    # 🎨 ОТТЕНОЧНЫЕ МАСКИ (2 фото)
    "mask_cold_chocolate": "Оттеночная маска Холодный шоколад",
    "mask_copper": "Оттеночная маска Медный",
    
    # 🖼 КОЛЛАЖ (1 фото)
    "collage_blonde": "Коллаж для блондинок"
}

class PhotoStorage:
    def __init__(self):
        self.storage = self._load_storage()
    
    def _load_storage(self):
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_storage(self):
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.storage, f, ensure_ascii=False, indent=2)
    
    def save_photo_id(self, key, file_id):
        self.storage[key] = file_id
        self._save_storage()
    
    def get_photo_id(self, key):
        return self.storage.get(key)
    
    def delete_photo(self, key):
        if key in self.storage:
            del self.storage[key]
            self._save_storage()
            return True
        return False
    
    def get_all_photos(self):
        return self.storage.copy()
    
    def get_missing_photos(self):
        missing = []
        for key in PHOTO_KEYS.keys():
            if key not in self.storage:
                missing.append(key)
        return missing
    
    def get_photo_status(self):
        status = {}
        for key, name in PHOTO_KEYS.items():
            status[name] = key in self.storage
        return status

# Глобальный экземпляр
photo_storage = PhotoStorage()
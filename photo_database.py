# photo_database.py - Хранилище фото в базе данных
import os
from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ========== ВСЕ КЛЮЧИ ФОТО ЗДЕСЬ ==========
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
    "collage_body": "Коллаж для тела",
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

# ========== НАСТРОЙКА БАЗЫ ДАННЫХ ==========
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///bot_data.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ========== МОДЕЛЬ ДЛЯ ХРАНЕНИЯ ФОТО ==========
class StoredPhoto(Base):
    __tablename__ = "stored_photos"
    
    photo_key = Column(String, primary_key=True)      # Ключ, например "body_milk"
    file_id = Column(String)                          # Telegram file_id
    display_name = Column(String)                     # Человеческое название

Base.metadata.create_all(engine)

# ========== КЛАСС ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ ==========
class DatabasePhotoStorage:
    def __init__(self):
        self.session = SessionLocal()
        self._init_database()
    
    def _init_database(self):
        """Заполняем базу всеми возможными ключами при первом запуске"""
        for key, name in PHOTO_KEYS.items():
            existing = self.session.get(StoredPhoto, key)
            if not existing:
                new_photo = StoredPhoto(
                    photo_key=key,
                    file_id=None,
                    display_name=name
                )
                self.session.add(new_photo)
        self.session.commit()
        print(f"✅ База данных фото инициализирована: {len(PHOTO_KEYS)} записей")
    
    def save_photo_id(self, key: str, file_id: str):
        """Сохраняем или обновляем file_id"""
        photo = self.session.get(StoredPhoto, key)
        if photo:
            photo.file_id = file_id
            self.session.commit()
            return True
        return False
    
    def get_photo_id(self, key: str):
        """Получаем file_id по ключу"""
        photo = self.session.get(StoredPhoto, key)
        if photo and photo.file_id:
            return photo.file_id
        return None
    
    def delete_photo(self, key: str):
        """Удаляем фото (очищаем file_id)"""
        photo = self.session.get(StoredPhoto, key)
        if photo:
            photo.file_id = None
            self.session.commit()
            return True
        return False
    
    def get_all_photos(self):
        """Получаем все загруженные фото"""
        result = {}
        photos = self.session.query(StoredPhoto).filter(
            StoredPhoto.file_id.isnot(None)
        ).all()
        
        for photo in photos:
            result[photo.photo_key] = photo.file_id
        
        return result
    
    def get_photo_status(self):
        """Получаем статус загрузки всех фото"""
        status = {}
        photos = self.session.query(StoredPhoto).all()
        
        for photo in photos:
            status[photo.display_name] = photo.file_id is not None
        
        return status
    
    def get_missing_photos(self):
        """Получаем список фото, которые еще не загружены"""
        missing = []
        photos = self.session.query(StoredPhoto).all()
        
        for photo in photos:
            if not photo.file_id:
                missing.append(photo.display_name)
        
        return missing

# Глобальный экземпляр хранилища
photo_storage = DatabasePhotoStorage()
# photo_database.py
import os
from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# === ВАЖНО: Для Render ===
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # На Render используем SQLite как временное хранилище
    # В будущем можно подключить PostgreSQL
    DATABASE_URL = "sqlite:///bot_data.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# === Таблица для фото ===
class StoredPhoto(Base):
    __tablename__ = "stored_photos"
    
    photo_key = Column(String, primary_key=True)  # Ключ, например "body_milk"
    file_id = Column(String)                      # Telegram file_id
    display_name = Column(String)                 # Человеческое название

Base.metadata.create_all(engine)

# === Импортируем старые названия ===
# Ваши PHOTO_KEYS из photo_storage.py
PHOTO_KEYS = {
    "body_milk": "Молочко для тела",
    # ... и все остальные ключи ...
    "collage_dandruff": "Коллаж: Перхоть/зуд"
}

# === Новый класс хранилища ===
class DatabasePhotoStorage:
    def __init__(self):
        self.session = SessionLocal()
        self._init_keys()
    
    def _init_keys(self):
        """Добавляем все возможные ключи в базу при первом запуске"""
        for key, name in PHOTO_KEYS.items():
            exists = self.session.get(StoredPhoto, key)
            if not exists:
                new_photo = StoredPhoto(
                    photo_key=key,
                    file_id=None,
                    display_name=name
                )
                self.session.add(new_photo)
        self.session.commit()
    
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
        return photo.file_id if photo and photo.file_id else None
    
    def delete_photo(self, key: str):
        """Удаляем file_id (оставляем запись в базе)"""
        photo = self.session.get(StoredPhoto, key)
        if photo:
            photo.file_id = None
            self.session.commit()
            return True
        return False
    
    def get_all_photos(self):
        """Все загруженные фото"""
        result = {}
        photos = self.session.query(StoredPhoto).filter(StoredPhoto.file_id.isnot(None)).all()
        for p in photos:
            result[p.photo_key] = p.file_id
        return result
    
    def get_photo_status(self):
        """Статус загрузки"""
        status = {}
        photos = self.session.query(StoredPhoto).all()
        for p in photos:
            status[p.display_name] = p.file_id is not None
        return status

# Глобальный экземпляр
photo_storage = DatabasePhotoStorage()
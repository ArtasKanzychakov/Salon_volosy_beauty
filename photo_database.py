# photo_database.py - Хранилище фото в БАЗЕ ДАННЫХ
import os
from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Импортируем PHOTO_KEYS из вашего старого файла
from photo_storage import PHOTO_KEYS

# ========== НАСТРОЙКА БАЗЫ ДАННЫХ ==========
# На Render используем SQLite, но сохраняем возможность для PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # Для локальной разработки
    DATABASE_URL = "sqlite:///bot_data.db"

# Создаем движок базы данных
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ========== МОДЕЛЬ ДЛЯ ХРАНЕНИЯ ФОТО ==========
class StoredPhoto(Base):
    __tablename__ = "stored_photos"
    
    # Ключ фото (например: "body_milk", "collage_blonde")
    photo_key = Column(String, primary_key=True)
    
    # Telegram file_id (уникальный идентификатор фото в Telegram)
    file_id = Column(String)
    
    # Человекочитаемое название (например: "Молочко для тела")
    display_name = Column(String)

# Создаем таблицу в базе данных
Base.metadata.create_all(engine)

# ========== КЛАСС ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ ==========
class DatabasePhotoStorage:
    def __init__(self):
        """Инициализация хранилища с базой данных"""
        self.session = SessionLocal()
        self._init_database()
    
    def _init_database(self):
        """Заполняем базу данных всеми возможными ключами при первом запуске"""
        for key, name in PHOTO_KEYS.items():
            # Проверяем, есть ли уже запись с таким ключом
            existing = self.session.get(StoredPhoto, key)
            if not existing:
                # Создаем новую запись без file_id
                new_photo = StoredPhoto(
                    photo_key=key,
                    file_id=None,
                    display_name=name
                )
                self.session.add(new_photo)
        self.session.commit()
        print(f"✅ База данных фото инициализирована: {len(PHOTO_KEYS)} записей")
    
    def save_photo_id(self, key: str, file_id: str):
        """Сохраняем или обновляем file_id для указанного ключа"""
        photo = self.session.get(StoredPhoto, key)
        if photo:
            photo.file_id = file_id
            self.session.commit()
            print(f"💾 Фото сохранено в БД: {key} -> {file_id[:20]}...")
            return True
        else:
            print(f"❌ Ключ не найден в БД: {key}")
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
            print(f"🗑 Фото удалено из БД: {key}")
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
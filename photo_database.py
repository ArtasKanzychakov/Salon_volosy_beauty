import os
import sqlalchemy as db
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Text, Integer, DateTime
from datetime import datetime

# Получаем URL базы данных из переменных окружения Render
DATABASE_URL = os.environ.get("DATABASE_URL")

# Критически важная строка: Render иногда выдаёт 'postgres://', а SQLAlchemy требует 'postgresql://'
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Создаем движок для подключения к базе
engine = db.create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модель для хранения информации о фото
class ProductPhoto(Base):
    __tablename__ = "product_photos"

    id = Column(Integer, primary_key=True, index=True)
    product_key = Column(String(100), index=True)  # Ключ продукта (например, "shampoo_normal")
    category = Column(String(50))  # Категория ("волосы" или "тело")
    file_id = Column(Text)  # Telegram file_id
    file_type = Column(String(10))  # "photo" или "document"
    uploaded_at = Column(DateTime, default=datetime.utcnow)

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

# Функции для работы с базой
def save_photo_to_db(product_key: str, category: str, file_id: str, file_type: str = "photo"):
    """Сохраняет photo_id в базу данных"""
    session = SessionLocal()
    try:
        # Удаляем старые записи для этого продукта (чтобы обновить)
        session.query(ProductPhoto).filter(ProductPhoto.product_key == product_key).delete()

        photo_record = ProductPhoto(
            product_key=product_key,
            category=category,
            file_id=file_id,
            file_type=file_type
        )
        session.add(photo_record)
        session.commit()
        print(f"[DB] Saved photo for {product_key}, category: {category}, file_id: {file_id[:20]}...")
        return True
    except Exception as e:
        session.rollback()
        print(f"[DB ERROR] Failed to save photo: {e}")
        return False
    finally:
        session.close()

def get_photos_from_db(product_key: str):
    """Получает все photo_id для конкретного продукта"""
    session = SessionLocal()
    try:
        photos = session.query(ProductPhoto).filter(
            ProductPhoto.product_key == product_key
        ).all()
        return [photo.file_id for photo in photos]
    except Exception as e:
        print(f"[DB ERROR] Failed to get photos: {e}")
        return []
    finally:
        session.close()

def get_all_photos():
    """Получает все фото из базы (для админ-панели)"""
    session = SessionLocal()
    try:
        photos = session.query(ProductPhoto).all()
        return photos
    except Exception as e:
        print(f"[DB ERROR] Failed to get all photos: {e}")
        return []
    finally:
        session.close()

def delete_photo_from_db(photo_id: int):
    """Удаляет фото из базы по ID"""
    session = SessionLocal()
    try:
        photo = session.query(ProductPhoto).filter(ProductPhoto.id == photo_id).first()
        if photo:
            session.delete(photo)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        print(f"[DB ERROR] Failed to delete photo: {e}")
        return False
    finally:
        session.close()

def clear_category_photos(category: str):
    """Очищает все фото категории"""
    session = SessionLocal()
    try:
        session.query(ProductPhoto).filter(ProductPhoto.category == category).delete()
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"[DB ERROR] Failed to clear category: {e}")
        return False
    finally:
        session.close()

def count_photos_in_db():
    """Подсчитывает количество фото в базе"""
    session = SessionLocal()
    try:
        count = session.query(ProductPhoto).count()
        return count
    except Exception as e:
        print(f"[DB ERROR] Failed to count photos: {e}")
        return 0
    finally:
        session.close()

# ========== КОМПАТИБИЛЬНОСТЬ СО СТАРЫМ КОДОМ ==========
# Класс для обратной совместимости
class PhotoDatabase:
    def __init__(self):
        print("[DB] Initialized PhotoDatabase for compatibility")

    async def get_photo_id(self, key: str):
        """Получить file_id для ключа (асинхронная версия)"""
        photos = get_photos_from_db(key)
        return photos[0] if photos else None

    async def save_photo(self, key: str, file_id: str):
        """Сохранить фото (асинхронная версия)"""
        # Определяем категорию по ключу
        category = "волосы"  # по умолчанию
        if "body" in key or "hyaluronic" in key or "anticellulite" in key or "тело" in key:
            category = "тело"
        elif "blond" in key or "blonde" in key:
            category = "блондинки"
        elif "colored" in key:
            category = "окрашенные"
        elif "mask" in key:
            category = "оттеночные_маски"
        elif "reconstruct" in key or "biolipid" in key or "protein" in key:
            category = "волосы"

        return save_photo_to_db(key, category, file_id, "photo")

    async def count_photos(self):
        """Подсчитать фото в базе"""
        return count_photos_in_db()

    async def delete_photo(self, key: str):
        """Удалить фото по ключу"""
        session = SessionLocal()
        try:
            deleted_count = session.query(ProductPhoto).filter(ProductPhoto.product_key == key).delete()
            session.commit()
            return deleted_count > 0
        except Exception as e:
            session.rollback()
            print(f"[DB ERROR] Failed to delete photo: {e}")
            return False
        finally:
            session.close()

    async def init_db(self):
        """Инициализация БД (для совместимости)"""
        # Таблицы уже созданы при импорте модуля
        print("[DB] Database already initialized")
        return True

# Старая версия для обратной совместимости
class PhotoStorageCompat:
    def __init__(self):
        print("[DB] Initialized compatibility layer photo_storage")

    def get_photo_id(self, key: str):
        """Получить file_id для ключа (синхронная версия)"""
        photos = get_photos_from_db(key)
        return photos[0] if photos else None

    def save_photo_id(self, key: str, file_id: str):
        """Сохранить фото (синхронная версия)"""
        # Определяем категорию по ключу
        category = "волосы"  # по умолчанию
        if "body" in key or "hyaluronic" in key or "anticellulite" in key or "тело" in key:
            category = "тело"
        elif "blond" in key or "blonde" in key:
            category = "блондинки"
        elif "colored" in key:
            category = "окрашенные"
        elif "mask" in key:
            category = "оттеночные_маски"
        elif "reconstruct" in key or "biolipid" in key or "protein" in key:
            category = "волосы"

        return save_photo_to_db(key, category, file_id, "photo")

    def get_all_photos(self):
        """Получить все фото"""
        photos = get_all_photos()
        result = {}
        for photo in photos:
            result[photo.product_key] = photo.file_id
        return result

    def delete_photo(self, key: str):
        """Удалить фото по ключу"""
        session = SessionLocal()
        try:
            deleted_count = session.query(ProductPhoto).filter(ProductPhoto.product_key == key).delete()
            session.commit()
            return deleted_count > 0
        except Exception as e:
            session.rollback()
            print(f"[DB ERROR] Failed to delete photo: {e}")
            return False
        finally:
            session.close()

    def get_photo_status(self):
        """Получить статус загрузки фото"""
        status = {}
        try:
            from config import PHOTO_KEYS
            for name, key in PHOTO_KEYS.items():
                photos = get_photos_from_db(key)
                status[name] = bool(photos)
        except ImportError:
            print("[DB WARNING] PHOTO_KEYS not found in config")
        return status

# Создаем экземпляры для импорта
photo_storage = PhotoStorageCompat()
photo_db = PhotoDatabase()  # Для совместимости с main.py

# Проверка подключения при импорте
try:
    connection = engine.connect()
    print("[DB] ✅ Successfully connected to PostgreSQL database")
    connection.close()
except Exception as e:
    print(f"[DB] ❌ Failed to connect to database: {e}")

# Словарь ключей продуктов
PHOTO_KEYS = {
    # Тело
    "body_milk": "Молочко для тела",
    "hydrophilic_oil": "Гидрофильное масло",
    "cream_body": "Крем-суфле",
    "body_scrub": "Скраб кофе/кокос",
    "shower_gel": "Гель для душа (вишня/манго/лимон)",
    "body_butter": "Баттер для тела",
    "hyaluronic_acid": "Гиалуроновая кислота для лица",
    "anticellulite_scrub": "Антицеллюлитный скраб (мята)",

    # Волосы - общие
    "biolipid_spray": "Биолипидный спрей",
    "dry_oil_spray": "Сухое масло спрей",
    "oil_elixir": "Масло ELIXIR",
    "hair_milk": "Молочко для волос",
    "oil_concentrate": "Масло-концентрат",
    "hair_fluid": "Флюид для волос",
    "reconstruct_shampoo": "Шампунь реконстракт",
    "reconstruct_mask": "Маска реконстракт",
    "protein_cream": "Протеиновый крем",

    # Блондинки
    "blonde_shampoo": "Шампунь для осветленных волос с гиалуроновой кислотой",
    "blonde_conditioner": "Кондиционер для осветленных волос с гиалуроновой кислотой",
    "blonde_mask": "Маска для осветленных волос с гиалуроновой кислотой",

    # Окрашенные
    "colored_shampoo": "Шампунь для окрашенных волос с коллагеном",
    "colored_conditioner": "Кондиционер для окрашенных волос с коллагеном",
    "colored_mask": "Маска для окрашенных волос с коллагеном",

    # Оттеночные маски
    "mask_cold_chocolate": "Оттеночная маска Холодный шоколад",
    "mask_copper": "Оттеночная маска Медный",
}
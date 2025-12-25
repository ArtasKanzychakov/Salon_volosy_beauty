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
        photo_record = ProductPhoto(
            product_key=product_key,
            category=category,
            file_id=file_id,
            file_type=file_type
        )
        session.add(photo_record)
        session.commit()
        print(f"[DB] Saved photo for {product_key}, category: {category}, file_id: {file_id}")
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

# Проверка подключения при импорте
try:
    connection = engine.connect()
    print("[DB] ✅ Successfully connected to PostgreSQL database")
    connection.close()
except Exception as e:
    print(f"[DB] ❌ Failed to connect to database: {e}")
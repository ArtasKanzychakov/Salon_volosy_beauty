"""
PHOTO_DATABASE.PY - Работа с PostgreSQL
"""

import os
import asyncpg
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class PhotoDatabase:
    """Асинхронная база данных для хранения фото"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.is_connected = False
    
    async def init_db(self) -> bool:
        """Инициализация подключения к базе данных"""
        database_url = os.environ.get("DATABASE_URL", "")
        
        if not database_url:
            logger.error("DATABASE_URL не установлен!")
            return False
        
        try:
            # Исправляем URL если нужно
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            
            self.pool = await asyncpg.create_pool(
                dsn=database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            
            # Создаем таблицу для фото
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS product_photos (
                        id SERIAL PRIMARY KEY,
                        product_key VARCHAR(100) NOT NULL UNIQUE,
                        category VARCHAR(50) NOT NULL,
                        subcategory VARCHAR(100) NOT NULL,
                        display_name VARCHAR(200) NOT NULL,
                        file_id TEXT NOT NULL,
                        uploaded_at TIMESTAMP DEFAULT NOW()
                    )
                ''')
            
            self.is_connected = True
            logger.info("✅ База данных подключена")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к базе данных: {e}")
            return False
    
    async def save_photo(self, product_key: str, category: str, 
                        subcategory: str, display_name: str, 
                        file_id: str) -> bool:
        """Сохранение фото в базу данных"""
        if not self.is_connected:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO product_photos 
                    (product_key, category, subcategory, display_name, file_id)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (product_key) 
                    DO UPDATE SET 
                        file_id = EXCLUDED.file_id,
                        uploaded_at = NOW()
                ''', product_key, category, subcategory, display_name, file_id)
            
            logger.info(f"✅ Фото сохранено: {display_name} ({product_key})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения фото: {e}")
            return False
    
    async def get_photo_id(self, product_key: str) -> Optional[str]:
        """Получение file_id по ключу продукта"""
        if not self.is_connected:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT file_id FROM product_photos WHERE product_key = $1',
                    product_key
                )
            
            return row['file_id'] if row else None
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения фото: {e}")
            return None
    
    async def delete_photo(self, product_key: str) -> bool:
        """Удаление фото по ключу"""
        if not self.is_connected:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    'DELETE FROM product_photos WHERE product_key = $1',
                    product_key
                )
            
            return "DELETE" in result
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления фото: {e}")
            return False
    
    async def count_photos(self) -> int:
        """Подсчет количества фото в базе"""
        if not self.is_connected:
            return 0
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('SELECT COUNT(*) FROM product_photos')
                return row[0] if row else 0
                
        except Exception as e:
            logger.error(f"❌ Ошибка подсчета фото: {e}")
            return 0
    
    async def get_photos_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Получение фото по категории"""
        if not self.is_connected:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    'SELECT product_key, display_name, subcategory FROM product_photos WHERE category = $1 ORDER BY display_name',
                    category
                )
            
            return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения фото по категории: {e}")
            return []
    
    async def get_all_photos(self) -> List[Dict[str, Any]]:
        """Получение всех фото из базы"""
        if not self.is_connected:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    'SELECT product_key, category, subcategory, display_name, uploaded_at FROM product_photos ORDER BY category, display_name'
                )
            
            return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения всех фото: {e}")
            return []
    
    async def close(self):
        """Закрытие соединения с базой данных"""
        if self.pool:
            await self.pool.close()
            self.is_connected = False

# Глобальный экземпляр
photo_db = PhotoDatabase()
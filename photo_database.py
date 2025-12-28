"""
PHOTO_DATABASE.PY - Работа с PostgreSQL базой данных
С улучшенной обработкой ошибок и мониторингом
"""

import os
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

# Асинхронные импорты
try:
    import asyncpg
    from asyncpg.pool import Pool
    HAS_ASYNC_PG = True
except ImportError:
    HAS_ASYNC_PG = False
    logging.warning("asyncpg не установлен. Работа с БД будет ограничена.")

logger = logging.getLogger(__name__)

class PhotoDatabase:
    """Асинхронная база данных для хранения фото"""
    
    def __init__(self):
        self.pool: Optional[Pool] = None
        self.is_connected = False
        self.connection_string = self._get_connection_string()
        logger.info("Инициализирована PhotoDatabase")
    
    def _get_connection_string(self) -> str:
        """Получение строки подключения к PostgreSQL"""
        database_url = os.environ.get("DATABASE_URL", "")
        
        if not database_url:
            logger.error("DATABASE_URL не установлен в переменных окружения!")
            return ""
        
        # Исправление формата для SQLAlchemy/asyncpg
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        logger.info(f"Строка подключения: {database_url[:50]}...")
        return database_url
    
    async def init_db(self) -> bool:
        """Инициализация подключения к базе данных"""
        if not HAS_ASYNC_PG:
            logger.error("asyncpg не установлен. Установите: pip install asyncpg")
            return False
        
        if not self.connection_string:
            logger.error("Не удалось получить строку подключения")
            return False
        
        try:
            # Создаем пул соединений
            self.pool = await asyncpg.create_pool(
                dsn=self.connection_string,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            
            # Создаем таблицу если её нет
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS product_photos (
                        id SERIAL PRIMARY KEY,
                        product_key VARCHAR(100) NOT NULL,
                        category VARCHAR(50) NOT NULL,
                        file_id TEXT NOT NULL,
                        file_type VARCHAR(20) DEFAULT 'photo',
                        uploaded_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(product_key)
                    )
                ''')
                
                # Создаем индекс для быстрого поиска
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_product_key 
                    ON product_photos(product_key)
                ''')
            
            self.is_connected = True
            logger.info("✅ База данных инициализирована и подключена")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к базе данных: {e}")
            self.is_connected = False
            return False
    
    async def save_photo(self, product_key: str, file_id: str, 
                        category: str = "unknown") -> bool:
        """Сохранение фото в базу данных"""
        if not self.is_connected or not self.pool:
            logger.error("Нет подключения к базе данных")
            return False
        
        try:
            async with self.pool.acquire() as conn:
                # Вставка или обновление записи
                await conn.execute('''
                    INSERT INTO product_photos (product_key, category, file_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (product_key) 
                    DO UPDATE SET 
                        file_id = EXCLUDED.file_id,
                        uploaded_at = NOW()
                ''', product_key, category, file_id)
            
            logger.info(f"✅ Фото сохранено: {product_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения фото {product_key}: {e}")
            return False
    
    async def get_photo_id(self, product_key: str) -> Optional[str]:
        """Получение file_id по ключу продукта"""
        if not self.is_connected or not self.pool:
            logger.error("Нет подключения к базе данных")
            return None
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT file_id FROM product_photos WHERE product_key = $1',
                    product_key
                )
            
            if row:
                return row['file_id']
            else:
                logger.debug(f"Фото не найдено: {product_key}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения фото {product_key}: {e}")
            return None
    
    async def delete_photo(self, product_key: str) -> bool:
        """Удаление фото по ключу"""
        if not self.is_connected or not self.pool:
            logger.error("Нет подключения к базе данных")
            return False
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    'DELETE FROM product_photos WHERE product_key = $1',
                    product_key
                )
            
            deleted = "DELETE" in result
            if deleted:
                logger.info(f"✅ Фото удалено: {product_key}")
            else:
                logger.info(f"Фото не найдено для удаления: {product_key}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления фото {product_key}: {e}")
            return False
    
    async def count_photos(self) -> int:
        """Подсчет количества фото в базе"""
        if not self.is_connected or not self.pool:
            return 0
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('SELECT COUNT(*) as count FROM product_photos')
                return row['count'] if row else 0
                
        except Exception as e:
            logger.error(f"❌ Ошибка подсчета фото: {e}")
            return 0
    
    async def get_all_photos(self) -> List[Dict[str, Any]]:
        """Получение всех фото из базы"""
        if not self.is_connected or not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    'SELECT product_key, category, uploaded_at FROM product_photos ORDER BY uploaded_at DESC'
                )
            
            return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения всех фото: {e}")
            return []
    
    async def clear_all_photos(self) -> bool:
        """Очистка всех фото из базы"""
        if not self.is_connected or not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('DELETE FROM product_photos')
            
            logger.info("✅ Все фото удалены из базы данных")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки базы данных: {e}")
            return False
    
    async def close(self):
        """Закрытие соединения с базой данных"""
        if self.pool:
            await self.pool.close()
            self.is_connected = False
            logger.info("Соединение с базой данных закрыто")

# Глобальный экземпляр базы данных
photo_db = PhotoDatabase()

async def init_database():
    """Инициализация базы данных"""
    return await photo_db.init_db()
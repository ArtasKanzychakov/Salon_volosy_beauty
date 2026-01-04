import asyncpg
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PhotoDatabase:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    @property
    def is_connected(self) -> bool:
        """Проверка подключения к базе данных"""
        return self.pool is not None and not self.pool._closed

    async def init(self):
        """
        Инициализация пула и таблицы.
        Вызывается ОДИН раз при старте бота.
        """
        if self.pool:
            return

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL not set")

        # Добавляем поддержку Render PostgreSQL
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        try:
            self.pool = await asyncpg.create_pool(
                dsn=database_url,
                min_size=1,
                max_size=5,
                command_timeout=30,
                ssl="require"  # Для Render PostgreSQL
            )
            await self._ensure_table()
            logger.info("✅ Photo database initialized successfully")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

    async def _ensure_table(self):
        """
        Создаёт таблицу, если её нет.
        НИКОГДА ничего не удаляет.
        """
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS product_photos (
                    id SERIAL PRIMARY KEY,
                    product_key TEXT UNIQUE NOT NULL,
                    category TEXT,
                    subcategory TEXT,
                    display_name TEXT,
                    file_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            logger.debug("✅ Table check/creation completed")

    async def save_photo(
        self,
        product_key: str,
        file_id: str,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        display_name: Optional[str] = None
    ) -> bool:
        """
        Сохраняет фото в базу данных
        Возвращает True при успехе, False при ошибке
        """
        if not self.pool:
            raise RuntimeError("Database not initialized")

        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO product_photos (
                        product_key, category, subcategory, display_name, file_id
                    )
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (product_key)
                    DO UPDATE SET
                        file_id = EXCLUDED.file_id,
                        category = EXCLUDED.category,
                        subcategory = EXCLUDED.subcategory,
                        display_name = EXCLUDED.display_name,
                        created_at = NOW();
                """, product_key, category, subcategory, display_name, file_id)
                return True
        except Exception as e:
            logger.error(f"❌ Error saving photo {product_key}: {e}")
            return False

    async def get_photo_id(self, product_key: str) -> Optional[str]:
        if not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT file_id
                    FROM product_photos
                    WHERE product_key = $1
                """, product_key)
                return row["file_id"] if row else None
        except Exception as e:
            logger.error(f"❌ Error getting photo {product_key}: {e}")
            return None

    async def get_photos_by_category(self, category: str) -> list[dict]:
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT product_key, category, subcategory,
                           display_name, file_id, created_at
                    FROM product_photos
                    WHERE category = $1
                    ORDER BY created_at DESC
                """, category)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Error getting photos by category {category}: {e}")
            return []

    async def get_all_photos(self) -> list[dict]:
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT product_key, category, subcategory,
                           display_name, file_id, created_at
                    FROM product_photos
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Error getting all photos: {e}")
            return []

    async def count_photos(self) -> int:
        if not self.pool:
            return 0

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT COUNT(*) FROM product_photos")
                return result or 0
        except Exception as e:
            logger.error(f"❌ Error counting photos: {e}")
            return 0

    async def close(self):
        if self.pool and not self.pool._closed:
            await self.pool.close()
            self.pool = None
            logger.info("🛑 Photo database connection closed")


# Глобальный синглтон экземпляр
photo_db = PhotoDatabase()
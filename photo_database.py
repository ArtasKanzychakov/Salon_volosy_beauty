"""
PHOTO_DATABASE.PY
Финальная версия для Render + PostgreSQL
Хранение Telegram file_id (без локальных файлов)
"""

import os
import asyncpg
import logging
from typing import Optional, List

logger = logging.getLogger("PHOTO_DB")


class PhotoDatabase:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    # ==================== CONNECT ====================

    async def connect(self):
        if self.pool:
            return

        self.pool = await asyncpg.create_pool(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 5432)),
            ssl="require",
            min_size=1,
            max_size=5
        )

        logger.info("✅ PostgreSQL pool создан")
        await self._init_db()

    # ==================== INIT ====================

    async def _init_db(self):
        async with self.pool.acquire() as conn:
            # ❗ НИКОГДА НЕ DROP TABLE
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS product_photos (
                    id SERIAL PRIMARY KEY,
                    product_key TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("📦 Таблица product_photos готова")

    # ==================== SAVE ====================

    async def save_photo(
        self,
        product_key: str,
        category: str,
        subcategory: str,
        display_name: str,
        file_id: str
    ) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO product_photos (
                    product_key,
                    category,
                    subcategory,
                    display_name,
                    file_id
                )
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (product_key)
                DO UPDATE SET
                    category = EXCLUDED.category,
                    subcategory = EXCLUDED.subcategory,
                    display_name = EXCLUDED.display_name,
                    file_id = EXCLUDED.file_id,
                    created_at = CURRENT_TIMESTAMP
            """,
            product_key,
            category,
            subcategory,
            display_name,
            file_id)

            logger.info(f"📸 Фото сохранено: {product_key}")

    # ==================== GET ====================

    async def get_photo_id(self, product_key: str) -> Optional[str]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT file_id
                FROM product_photos
                WHERE product_key = $1
            """, product_key)

            if row:
                return row["file_id"]
            return None

    # ==================== LIST ====================

    async def get_all_photos(self) -> List[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT product_key,
                       category,
                       subcategory,
                       display_name,
                       created_at
                FROM product_photos
                ORDER BY created_at DESC
            """)

    # ==================== CLOSE ====================

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("🛑 PostgreSQL pool закрыт")


# ==================== SINGLETON ====================

photo_db = PhotoDatabase()
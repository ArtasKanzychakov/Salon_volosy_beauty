import asyncpg
import os
import logging

logger = logging.getLogger(__name__)


class PhotoDatabase:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None

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

        self.pool = await asyncpg.create_pool(
            database_url,
            min_size=1,
            max_size=5,
            command_timeout=30
        )

        await self._ensure_table()
        logger.info("✅ Photo database initialized")

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

    async def save_photo(
        self,
        product_key: str,
        file_id: str,
        category: str | None = None,
        subcategory: str | None = None,
        display_name: str | None = None
    ):
        if not self.pool:
            raise RuntimeError("Database not initialized")

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

    async def get_photo_id(self, product_key: str) -> str | None:
        if not self.pool:
            raise RuntimeError("Database not initialized")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT file_id
                FROM product_photos
                WHERE product_key = $1
            """, product_key)

            return row["file_id"] if row else None

    async def get_all_photos(self) -> list[dict]:
        if not self.pool:
            raise RuntimeError("Database not initialized")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT product_key, category, subcategory,
                       display_name, file_id, created_at
                FROM product_photos
                ORDER BY created_at DESC
            """)

            return [dict(row) for row in rows]

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("🛑 Photo database connection closed")


# ✅ ГЛОБАЛЬНЫЙ SINGLETON (ОБЯЗАТЕЛЬНО ВНЕ КЛАССА)
photo_db = PhotoDatabase()

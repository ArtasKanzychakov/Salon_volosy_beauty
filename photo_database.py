import asyncpg
import os


class PhotoDatabase:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            ssl="require"
        )
        await self.init_db()

    async def init_db(self):
        async with self.pool.acquire() as conn:
            # ❗ НИ В КОЕМ СЛУЧАЕ НЕ DROP TABLE
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS product_photos (
                    id SERIAL PRIMARY KEY,
                    product_key VARCHAR(100) UNIQUE NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    subcategory VARCHAR(100) NOT NULL,
                    display_name VARCHAR(200) NOT NULL,
                    file_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    async def save_photo(
        self,
        product_key: str,
        category: str,
        subcategory: str,
        display_name: str,
        file_id: str
    ):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO product_photos (
                    product_key, category, subcategory, display_name, file_id
                )
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (product_key)
                DO UPDATE SET
                    file_id = EXCLUDED.file_id,
                    display_name = EXCLUDED.display_name,
                    category = EXCLUDED.category,
                    subcategory = EXCLUDED.subcategory,
                    created_at = CURRENT_TIMESTAMP
            """, product_key, category, subcategory, display_name, file_id)

    async def get_photo_id(self, product_key: str) -> str | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT file_id
                FROM product_photos
                WHERE product_key = $1
            """, product_key)

            if row:
                return row["file_id"]
            return None
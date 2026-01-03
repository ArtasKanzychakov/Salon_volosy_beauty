import asyncio
from photo_database import PhotoDatabase


async def main():
    db = PhotoDatabase()
    await db.init()

    await db.save_photo(
        product_key="test_product",
        file_id="TEST_FILE_ID",
        category="test",
        subcategory="test",
        display_name="Test Product"
    )

    file_id = await db.get_photo_id("test_product")
    print("file_id:", file_id)

    all_photos = await db.get_all_photos()
    print("all_photos:", all_photos)

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())

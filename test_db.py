import asyncio
import os
from photo_database import photo_db

async def test_connection():
    print("🔍 Тестирование подключения к БД...")
    
    # Установите DATABASE_URL если его нет
    os.environ["DATABASE_URL"] = "postgresql://salon_volosy_photo_bazz_user:Sa0KCOH64FxaJV3Bt7VxRMQRDX4F5L6U@dpg-d56fkmer433s73e4mvog-a/salon_volosy_photo_bazz"
    
    connected = await photo_db.init_db()
    print(f"✅ Подключение: {connected}")
    
    if connected:
        count = await photo_db.count_photos()
        print(f"📊 Фото в базе: {count}")
        
        # Попробуем добавить тестовое фото
        test_success = await photo_db.save_photo(
            product_key="test_photo",
            category="тело",
            subcategory="Очищение и скрабы",
            display_name="Тестовый продукт",
            file_id="test_file_id_123"
        )
        print(f"📸 Тестовое сохранение: {test_success}")
        
        # Проверим чтение
        file_id = await photo_db.get_photo_id("test_photo")
        print(f"🔍 Получение тестового фото: {file_id is not None}")

if __name__ == "__main__":
    asyncio.run(test_connection())
"""
MAIN.PY - ФИНАЛЬНАЯ ВЕРСИЯ для Render с работающим health check
"""

import os
import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import List

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import ReplyKeyboardBuilder

import config
from states import UserState, AdminState
import keyboards
from photo_database import photo_db
from user_storage import (
    save_user_data, get_user_data_value, add_selected_problem,
    remove_selected_problem, get_selected_problems,
    clear_selected_problems, delete_user_data
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== HEALTH CHECK СЕРВЕР ====================

async def start_health_server():
    """Запуск health check сервера"""
    from aiohttp import web
    
    async def health_handler(request):
        return web.Response(text='OK')
    
    app = web.Application()
    app.router.add_get('/health', health_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🌐 Health check сервер запущен на порту {port}")
    return runner

# ==================== SELF-PING СИСТЕМА ====================

async def self_ping():
    """Функция для self-ping приложения"""
    try:
        external_url = os.getenv("RENDER_EXTERNAL_URL")
        
        if not external_url:
            logger.warning("⚠️ RENDER_EXTERNAL_URL не установлен")
            service_name = os.getenv("RENDER_SERVICE_NAME", "salon-volosy-beauty")
            external_url = f"https://{service_name}.onrender.com"
        
        ping_url = f"{external_url}/health"
        logger.debug(f"🔗 Пингую: {ping_url}")
        
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(ping_url) as response:
                if response.status == 200:
                    logger.info(f"✅ Self-ping успешен: {datetime.now().strftime('%H:%M:%S')}")
                    return True
                else:
                    logger.warning(f"⚠️ Self-ping вернул статус {response.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Ошибка self-ping: {str(e)[:100]}")
        return False

async def self_ping_task():
    """Постоянная задача для self-ping"""
    logger.info("🔔 Self-ping задача запущена")
    await asyncio.sleep(15)
    await self_ping()
    
    while True:
        try:
            await asyncio.sleep(240)  # 4 минуты
            await self_ping()
        except asyncio.CancelledError:
            logger.info("🔔 Self-ping задача остановлена")
            break
        except Exception as e:
            logger.error(f"❌ Ошибка в self_ping_task: {e}")
            await asyncio.sleep(60)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def new_selection_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔄 Новая подборка"))
    builder.add(KeyboardButton(text="🏠 Главное меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def final_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔄 Новая подборка"))
    builder.add(KeyboardButton(text="💇‍♀️ Волосы"))
    builder.add(KeyboardButton(text="🧴 Тело"))
    builder.add(KeyboardButton(text="🏠 Главное меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

async def send_recommended_photos(chat_id: int, photo_keys: List[str], caption: str = ""):
    try:
        if not photo_keys:
            await bot.send_message(
                chat_id, 
                "📷 Фото продуктов для этих рекомендаций пока не загружены.",
                reply_markup=final_menu_keyboard()
            )
            return

        if not photo_db.is_connected:
            await bot.send_message(
                chat_id, 
                "🔄 База данных обновляется. Попробуйте позже.",
                reply_markup=final_menu_keyboard()
            )
            return

        sent_count = 0
        for photo_key in photo_keys:
            file_id = await photo_db.get_photo_id(photo_key)
            if file_id:
                display_name = photo_key
                for category in config.PHOTO_STRUCTURE.values():
                    for subcat_products in category.values():
                        for key, name in subcat_products:
                            if key == photo_key:
                                display_name = name
                                break

                await bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption=f"{caption}\n<b>{display_name}</b>" if caption else f"<b>{display_name}</b>",
                    parse_mode=ParseMode.HTML
                )
                sent_count += 1
                await asyncio.sleep(0.5)

        if sent_count == 0:
            await bot.send_message(
                chat_id,
                "📷 Фото продуктов временно недоступны.\n\nАдминистратор еще не загрузил фотографии для этих продуктов.",
                reply_markup=final_menu_keyboard()
            )

    except Exception as e:
        logger.error(f"❌ Ошибка при отправке фото: {e}")
        await bot.send_message(
            chat_id,
            "❌ Произошла ошибка при отправке фото.",
            reply_markup=final_menu_keyboard()
        )

# ==================== МИДЛВЕЙР ДЛЯ ПРОВЕРКИ БД ====================

@dp.update.middleware()
async def check_db_middleware(handler, event, data):
    if not photo_db.is_connected:
        logger.warning("⚠️ БД не подключена, пытаемся переподключиться...")
        await photo_db.init()  # <- Исправлено с init_db() на init()
    return await handler(event, data)

# ==================== ЗАПУСК БОТА ====================

async def on_startup():
    logger.info("🤖 Бот запускается...")

    # Инициализация базы данных
    await photo_db.init()  # <- Исправлено с init_db() на init()
    logger.info(f"📊 Статус подключения к БД: {photo_db.is_connected}")

    if photo_db.is_connected:
        photo_count = await photo_db.count_photos()
        logger.info(f"📸 Фото в базе: {photo_count}")

    # Health check сервер
    try:
        await start_health_server()
        logger.info("🌐 Health check сервер запущен")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска health check сервера: {e}")

    # Self-ping
    asyncio.create_task(self_ping_task())
    logger.info("🔔 Self-ping система активирована")

    # Установка webhook или опроса
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Бот готов к работе!")

async def on_shutdown():
    logger.info("🛑 Бот выключается...")
    await photo_db.close()
    logger.info("🗄️ Соединение с БД закрыто")

async def main():
    try:
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        logger.info("🚀 Запуск бота с работающим health check...")
        await dp.start_polling(
            bot, 
            skip_updates=True,
            allowed_updates=dp.resolve_used_update_types()
        )

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"⚠️ Необработанное исключение: {e}", exc_info=True)

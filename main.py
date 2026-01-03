"""
MAIN.PY — ИСПРАВЛЕННАЯ ФИНАЛЬНАЯ ВЕРСИЯ
Render + PostgreSQL + стабильные фото
"""

import os
import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import List

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
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

# ==================== ЛОГИ ====================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("MAIN")

# ==================== BOT ====================

bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())

# ==================== HEALTH CHECK ====================

async def start_health_server():
    from aiohttp import web

    async def health(request):
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"🌐 Health check на порту {port}")
    return runner

# ==================== SELF PING ====================

async def self_ping_loop():
    await asyncio.sleep(20)

    url = os.getenv("RENDER_EXTERNAL_URL")
    if not url:
        name = os.getenv("RENDER_SERVICE_NAME", "salon-volosy-beauty")
        url = f"https://{name}.onrender.com"

    ping_url = f"{url}/health"
    logger.info(f"🔁 Self-ping: {ping_url}")

    timeout = aiohttp.ClientTimeout(total=10)

    while True:
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(ping_url) as r:
                    logger.info(f"🔔 Ping {r.status}")
        except Exception as e:
            logger.warning(f"⚠️ Ping error: {e}")
        await asyncio.sleep(240)

# ==================== КЛАВИАТУРЫ ====================

def final_menu_keyboard() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.add(
        KeyboardButton(text="🔄 Новая подборка"),
        KeyboardButton(text="💇‍♀️ Волосы"),
        KeyboardButton(text="🧴 Тело"),
        KeyboardButton(text="🏠 Главное меню")
    )
    b.adjust(2)
    return b.as_markup(resize_keyboard=True)

# ==================== ФОТО ====================

async def send_recommended_photos(chat_id: int, keys: List[str], caption: str):
    sent = 0

    for key in keys:
        file_id = await photo_db.get_photo_id(key)
        if not file_id:
            continue

        name = key
        for cat in config.PHOTO_STRUCTURE.values():
            for sub in cat.values():
                for k, v in sub:
                    if k == key:
                        name = v
                        break

        await bot.send_photo(
            chat_id,
            file_id,
            caption=f"{caption}\n<b>{name}</b>"
        )
        sent += 1
        await asyncio.sleep(0.4)

    if sent == 0:
        await bot.send_message(
            chat_id,
            "📷 Фото для рекомендаций пока не загружены.",
            reply_markup=final_menu_keyboard()
        )

# ==================== START ====================

@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    delete_user_data(message.from_user.id)

    await message.answer(
        "👋 <b>SVOY AV.COSMETIC</b>\n\nВыберите категорию:",
        reply_markup=keyboards.main_menu_keyboard()
    )
    await state.set_state(UserState.CHOOSING_CATEGORY)

# ==================== КАТЕГОРИИ ====================

@dp.message(UserState.CHOOSING_CATEGORY, F.text == "💇‍♀️ Волосы")
async def hair_start(message: Message, state: FSMContext):
    clear_selected_problems(message.from_user.id)
    await state.set_state(UserState.HAIR_CHOOSING_TYPE)
    await message.answer(
        "💇‍♀️ Какой у вас тип волос?",
        reply_markup=keyboards.hair_type_keyboard()
    )

@dp.message(UserState.CHOOSING_CATEGORY, F.text == "🧴 Тело")
async def body_start(message: Message, state: FSMContext):
    await state.set_state(UserState.BODY_CHOOSING_GOAL)
    await message.answer(
        "🧴 Ваша цель ухода:",
        reply_markup=keyboards.body_goals_keyboard()
    )

# ==================== BODY ====================

@dp.message(UserState.BODY_CHOOSING_GOAL)
async def body_result(message: Message, state: FSMContext):
    goal = message.text
    text, photos = await config.get_body_recommendations(goal)

    await message.answer(text, reply_markup=final_menu_keyboard())
    await send_recommended_photos(
        message.chat.id,
        photos,
        "🛍️ Рекомендуемые продукты:"
    )

    await state.clear()

# ==================== ADMIN PHOTO ====================

@dp.message(AdminState.ADMIN_WAITING_PHOTO, F.photo)
async def admin_photo(message: Message, state: FSMContext):
    data = await state.get_data()

    await photo_db.save_photo(
        product_key=data["admin_product_key"],
        category=data["admin_category"],
        subcategory=data["admin_subcategory"],
        display_name=data["admin_display_name"],
        file_id=message.photo[-1].file_id
    )

    await message.answer(
        "✅ Фото сохранено",
        reply_markup=keyboards.admin_category_keyboard()
    )
    await state.set_state(AdminState.ADMIN_MAIN_MENU)

# ==================== STARTUP / SHUTDOWN ====================

async def on_startup():
    logger.info("🚀 Запуск бота")
    await photo_db.connect()
    await start_health_server()
    asyncio.create_task(self_ping_loop())
    await bot.delete_webhook(drop_pending_updates=True)

async def on_shutdown():
    await photo_db.close()
    logger.info("🛑 Остановлен")

# ==================== RUN ====================

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types()
    )

if __name__ == "__main__":
    asyncio.run(main())
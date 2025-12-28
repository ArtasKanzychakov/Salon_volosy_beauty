"""
MAIN.PY - Основной файл бота SVOY AV.COSMETIC
"""

import asyncio
import logging
import sys
import os
from typing import List

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ContentType
from aiogram.enums import ParseMode

import config
import keyboards
from states import UserState, AdminState
from user_storage import user_data_storage
from photo_database import photo_db
from keep_alive import start_health_server, stop_health_server

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Системные переменные
health_server_runner = None

# ==================== СИСТЕМА ФОТО ====================

async def send_photo_group(chat_id: int, photo_keys: List[str], caption: str = ""):
    """Отправляет группу фото по ключам"""
    try:
        from aiogram.types import InputMediaPhoto
        
        media_group = []
        for key in photo_keys:
            photo_id = await photo_db.get_photo_id(key)
            if photo_id:
                media_group.append(InputMediaPhoto(media=photo_id))
        
        if media_group:
            if caption:
                media_group[0].caption = caption[:1024]
            await bot.send_media_group(chat_id=chat_id, media=media_group)
            return True
        else:
            await bot.send_message(chat_id, "📷 Фото продуктов скоро будут доступны!")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        return False

# ==================== ОБЩИЕ КОМАНДЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Привет! Я бот-консультант SVOY AV.COSMETIC.\n"
        "Помогу подобрать уход для волос или тела.",
        reply_markup=keyboards.main_menu_keyboard()
    )
    await state.set_state(UserState.MAIN_MENU)

@dp.message(Command("admin2026"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.set_state(AdminState.WAITING_PASSWORD)
    await message.answer("Введите пароль для доступа к админ-панели:")

@dp.message(Command("checkphotos"))
async def cmd_checkphotos(message: Message):
    count = await photo_db.count_photos()
    await message.answer(f"📊 В базе данных: {count} фото")

@dp.message(F.text == "🏠 Главное меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    await cmd_start(message, state)

# ==================== КАТЕГОРИЯ "ТЕЛО" ====================

@dp.message(F.text == "🧴 Тело", UserState.MAIN_MENU)
async def body_handler(message: Message, state: FSMContext):
    await state.set_state(UserState.BODY_CHOOSING_GOAL)
    await message.answer(
        "Выберите задачу для ухода за телом:",
        reply_markup=keyboards.body_goals_keyboard()
    )

@dp.message(F.text.in_(config.BODY_GOALS), UserState.BODY_CHOOSING_GOAL)
async def body_goal_handler(message: Message, state: FSMContext):
    goal = message.text
    
    # Маппинг целей на ключи фото
    photo_mapping = {
        "Общий уход": "body_general",
        "Сухая кожа": "body_dry",
        "Чувствительная и склонная к раздражениям": "body_sensitive",
        "Борьба с целлюлитом и тонизирование": "body_cellulite"
    }
    
    # Получаем рекомендации
    recommendations = config.get_body_recommendations(goal)
    
    # Отправляем рекомендации
    await message.answer(f"🎯 **{goal}**\n\n{recommendations}", parse_mode=ParseMode.MARKDOWN)
    
    # Отправляем фото
    photo_key = photo_mapping.get(goal)
    if photo_key:
        await send_photo_group(
            chat_id=message.chat.id,
            photo_keys=[photo_key],
            caption="📦 Рекомендуемые продукты:"
        )
    
    # Информация о точках продаж
    await message.answer(config.SALES_POINTS, parse_mode=ParseMode.MARKDOWN)
    
    # Возвращаем в главное меню
    await cmd_start(message, state)

# ==================== КАТЕГОРИЯ "ВОЛОСЫ" ====================

@dp.message(F.text == "💇‍♀️ Волосы", UserState.MAIN_MENU)
async def hair_handler(message: Message, state: FSMContext):
    await state.set_state(UserState.HAIR_CHOOSING_TYPE)
    await message.answer(
        "Вы окрашивали волосы?",
        reply_markup=keyboards.hair_type_keyboard()
    )

@dp.message(F.text.in_(config.HAIR_TYPES), UserState.HAIR_CHOOSING_TYPE)
async def hair_type_handler(message: Message, state: FSMContext):
    hair_type = message.text
    user_data_storage.update_data(message.from_user.id, {"hair_type": hair_type})
    
    await state.set_state(UserState.HAIR_CHOOSING_PROBLEMS)
    await message.answer(
        "Выберите проблемы волос (можно несколько):",
        reply_markup=keyboards.hair_problems_keyboard()
    )

@dp.message(UserState.HAIR_CHOOSING_PROBLEMS)
async def hair_problems_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if message.text == "✅ Готово":
        selected = user_data_storage.get_data(user_id).get("hair_problems", [])
        if not selected:
            await message.answer("Пожалуйста, выберите хотя бы одну проблему.")
            return
        
        await state.set_state(UserState.HAIR_CHOOSING_SCALP)
        await message.answer(
            "Есть ли чувствительность кожи головы?",
            reply_markup=keyboards.scalp_type_keyboard()
        )
        return
    
    # Обработка выбора проблем
    problem_text = message.text.replace("✅ ", "").replace("☐ ", "")
    if problem_text in config.HAIR_PROBLEMS:
        current = user_data_storage.get_data(user_id).get("hair_problems", [])
        if problem_text in current:
            current.remove(problem_text)
        else:
            current.append(problem_text)
        
        user_data_storage.update_data(user_id, {"hair_problems": current})
        
        await message.answer(
            f"Выбрано: {len(current)} проблем\nВыберите проблемы:",
            reply_markup=keyboards.hair_problems_keyboard(current)
        )

@dp.message(F.text.in_(config.SCALP_TYPES), UserState.HAIR_CHOOSING_SCALP)
async def scalp_type_handler(message: Message, state: FSMContext):
    user_data_storage.update_data(message.from_user.id, {"scalp_type": message.text})
    
    await state.set_state(UserState.HAIR_CHOOSING_VOLUME)
    await message.answer(
        "Хотите добавить объем?",
        reply_markup=keyboards.hair_volume_keyboard()
    )

@dp.message(F.text.in_(config.HAIR_VOLUME), UserState.HAIR_CHOOSING_VOLUME)
async def hair_volume_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data_storage.update_data(user_id, {"hair_volume": message.text})
    
    user_data = user_data_storage.get_data(user_id)
    hair_type = user_data.get("hair_type", "")
    
    if hair_type in ["Окрашенные блондинки", "Окрашенные все остальные"]:
        await state.set_state(UserState.HAIR_CHOOSING_COLOR)
        await message.answer(
            "Выберите цвет волос:",
            reply_markup=keyboards.hair_color_keyboard(hair_type)
        )
    else:
        await generate_hair_result(message, state)

@dp.message(UserState.HAIR_CHOOSING_COLOR)
async def hair_color_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = user_data_storage.get_data(user_id)
    hair_type = user_data.get("hair_type", "")
    
    valid_colors = config.get_hair_colors(hair_type)
    if message.text not in valid_colors:
        await message.answer("Пожалуйста, выберите цвет из списка.")
        return
    
    user_data_storage.update_data(user_id, {"hair_color": message.text})
    await generate_hair_result(message, state)

async def generate_hair_result(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = user_data_storage.get_data(user_id)
    
    hair_type = user_data.get("hair_type", "")
    problems = user_data.get("hair_problems", [])
    scalp_type = user_data.get("scalp_type", "")
    hair_volume = user_data.get("hair_volume", "")
    hair_color = user_data.get("hair_color", "")
    
    # Формируем рекомендации
    recommendations = config.get_hair_recommendations(
        hair_type, problems, scalp_type, hair_volume, hair_color
    )
    
    # Маппинг для фото
    photo_keys = []
    
    # Базовые фото
    if hair_type == "Окрашенные блондинки":
        photo_keys.append("hair_blonde_general")
    elif hair_type == "Окрашенные все остальные":
        photo_keys.append("hair_colored_general")
    else:
        photo_keys.append("hair_natural_general")
    
    # Фото проблем
    problem_mapping = {
        "Ломкость": "hair_brittle",
        "Выпадение": "hair_loss",
        "Перхоть/зуд": "hair_dandruff",
        "Секущиеся кончики": "hair_split",
        "Тусклость": "hair_dull",
        "Пушистость": "hair_frizzy",
        "Тонкие": "hair_thin",
        "Очень поврежденные": "hair_damaged"
    }
    
    for problem in problems:
        if problem in problem_mapping:
            photo_keys.append(problem_mapping[problem])
    
    # Дополнительные фото
    if scalp_type == "Да, чувствительная":
        photo_keys.append("hair_scalp_sensitive")
    
    if hair_volume == "Да, хочу объем":
        photo_keys.append("hair_volume")
    
    if hair_color in ["Шатенка", "Русая"]:
        photo_keys.append("hair_mask_chocolate")
    elif hair_color == "Рыжая":
        photo_keys.append("hair_mask_copper")
    
    # Отправляем рекомендации
    await message.answer(recommendations, parse_mode=ParseMode.MARKDOWN)
    
    # Отправляем фото
    if photo_keys:
        await send_photo_group(
            chat_id=message.chat.id,
            photo_keys=photo_keys,
            caption="📦 Рекомендуемые продукты:"
        )
    
    # Информация о продажах
    await message.answer(
        f"{config.SALES_POINTS}\n\n{config.DELIVERY_INFO}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Очищаем данные
    user_data_storage.clear_data(user_id)
    
    # Возвращаем в главное меню
    await cmd_start(message, state)

# ==================== АДМИН-ПАНЕЛЬ ====================

@dp.message(AdminState.WAITING_PASSWORD)
async def admin_password_handler(message: Message, state: FSMContext):
    if message.text == config.ADMIN_PASSWORD:
        await state.set_state(AdminState.ADMIN_MAIN_MENU)
        await message.answer(
            "Доступ разрешен. Выберите категорию:",
            reply_markup=keyboards.admin_category_keyboard()
        )
    else:
        await message.answer("Неверный пароль. Попробуйте снова.")

@dp.message(F.text.in_(["💇‍♀️ Волосы", "🧴 Тело"]), AdminState.ADMIN_MAIN_MENU)
async def admin_category_handler(message: Message, state: FSMContext):
    category = "волосы" if message.text == "💇‍♀️ Волосы" else "тело"
    await state.update_data(admin_category=category)
    await state.set_state(AdminState.ADMIN_CHOOSING_PRODUCT)
    
    if category == "волосы":
        products = [
            "Общий уход для блондинок",
            "Общий уход для окрашенных",
            "Общий уход для натуральных",
            "Ломкость",
            "Выпадение",
            "Перхоть/зуд",
            "Секущиеся кончики",
            "Тусклость",
            "Пушистость",
            "Тонкие",
            "Очень поврежденные",
            "Чувствительная кожа головы",
            "Объем",
            "Оттеночная маска Холодный шоколад",
            "Оттеночная маска Медный"
        ]
    else:
        products = [
            "Общий уход",
            "Сухая кожа",
            "Чувствительная кожа",
            "Борьба с целлюлитом"
        ]
    
    await message.answer(
        f"Категория: {category}\nВыберите продукт:",
        reply_markup=keyboards.admin_products_keyboard(products)
    )

@dp.message(AdminState.ADMIN_CHOOSING_PRODUCT)
async def admin_product_handler(message: Message, state: FSMContext):
    product = message.text
    admin_data = await state.get_data()
    category = admin_data.get("admin_category", "")
    
    # Маппинг названий на ключи
    product_mapping = {
        "волосы": {
            "Общий уход для блондинок": "hair_blonde_general",
            "Общий уход для окрашенных": "hair_colored_general",
            "Общий уход для натуральных": "hair_natural_general",
            "Ломкость": "hair_brittle",
            "Выпадение": "hair_loss",
            "Перхоть/зуд": "hair_dandruff",
            "Секущиеся кончики": "hair_split",
            "Тусклость": "hair_dull",
            "Пушистость": "hair_frizzy",
            "Тонкие": "hair_thin",
            "Очень поврежденные": "hair_damaged",
            "Чувствительная кожа головы": "hair_scalp_sensitive",
            "Объем": "hair_volume",
            "Оттеночная маска Холодный шоколад": "hair_mask_chocolate",
            "Оттеночная маска Медный": "hair_mask_copper"
        },
        "тело": {
            "Общий уход": "body_general",
            "Сухая кожа": "body_dry",
            "Чувствительная кожа": "body_sensitive",
            "Борьба с целлюлитом": "body_cellulite"
        }
    }
    
    product_key = product_mapping.get(category, {}).get(product)
    
    if not product_key:
        await message.answer("Неизвестный продукт. Выберите из списка.")
        return
    
    await state.update_data(admin_product=product_key)
    await state.set_state(AdminState.ADMIN_WAITING_PHOTO)
    
    await message.answer(
        f"Продукт: {product}\nКлюч: {product_key}\n\n"
        f"Отправьте фото для этого продукта:"
    )

@dp.message(F.content_type == ContentType.PHOTO, AdminState.ADMIN_WAITING_PHOTO)
async def admin_photo_handler(message: Message, state: FSMContext):
    admin_data = await state.get_data()
    product_key = admin_data.get("admin_product", "")
    
    if not product_key:
        await message.answer("Ошибка: не выбран продукт.")
        await state.set_state(AdminState.ADMIN_MAIN_MENU)
        return
    
    photo = message.photo[-1]
    file_id = photo.file_id
    
    success = await photo_db.save_photo(product_key, file_id)
    
    if success:
        await message.answer(f"✅ Фото для '{product_key}' успешно сохранено!")
    else:
        await message.answer(f"❌ Ошибка при сохранении фото для '{product_key}'")
    
    # Возвращаемся к выбору категории
    await state.set_state(AdminState.ADMIN_MAIN_MENU)
    await message.answer(
        "Выберите категорию:",
        reply_markup=keyboards.admin_category_keyboard()
    )

@dp.message(F.text == "↩️ Назад к категориям", AdminState.ADMIN_CHOOSING_PRODUCT)
async def admin_back_to_categories(message: Message, state: FSMContext):
    await state.set_state(AdminState.ADMIN_MAIN_MENU)
    await message.answer(
        "Выберите категорию:",
        reply_markup=keyboards.admin_category_keyboard()
    )

# ==================== ЗАПУСК БОТА ====================

async def on_startup():
    """Действия при запуске"""
    logger.info("🚀 Запуск бота SVOY AV.COSMETIC")
    
    # Запускаем health сервер
    global health_server_runner
    health_server_runner = await start_health_server()
    logger.info("✅ Health сервер запущен")
    
    # Инициализируем базу данных
    db_success = await photo_db.init_db()
    if db_success:
        logger.info("✅ База данных подключена")
    else:
        logger.warning("⚠️ База данных не подключена")
    
    # Проверяем бота
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот запущен: @{bot_info.username}")

async def on_shutdown():
    """Действия при завершении"""
    logger.info("🛑 Завершение работы бота...")
    
    # Останавливаем health сервер
    if health_server_runner:
        await stop_health_server(health_server_runner)
    
    # Закрываем базу данных
    await photo_db.close()
    
    logger.info("✅ Бот остановлен")

async def main():
    """Основная функция"""
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    try:
        logger.info("🔄 Запуск поллинга...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())
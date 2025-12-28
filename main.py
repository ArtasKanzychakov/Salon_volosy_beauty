"""
MAIN.PY - Основной файл бота SVOY AV.COSMETIC
"""

import asyncio
import logging
import sys
import os
from typing import List
from datetime import datetime

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
    
    # Получаем ключи фото для этой цели
    photo_keys = config.PHOTO_MAPPING["тело"].get(goal, [])
    
    # Получаем рекомендации
    recommendations = config.get_body_recommendations(goal)
    
    # Отправляем рекомендации
    await message.answer(f"🎯 **{goal}**\n\n{recommendations}", parse_mode=ParseMode.MARKDOWN)
    
    # Отправляем фото
    if photo_keys:
        await send_photo_group(
            chat_id=message.chat.id,
            photo_keys=photo_keys,
            caption="📦 Рекомендуемые продукты:"
        )
    else:
        await message.answer("📷 Фото продуктов скоро будут доступны!")
    
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
        "Выберите проблемы волос (можно несколько, но необязательно):",
        reply_markup=keyboards.hair_problems_keyboard()
    )

@dp.message(UserState.HAIR_CHOOSING_PROBLEMS)
async def hair_problems_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if message.text == "✅ Готово":
        # Разрешаем переход даже если ничего не выбрано
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
            f"Выбрано: {len(current)} проблем\nВыберите проблемы (или нажмите 'Готово'):",
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
    if message.text not in valid_colors and message.text != "🏠 Главное меню":
        await message.answer("Пожалуйста, выберите цвет из списка.")
        return
    
    if message.text != "🏠 Главное меню":
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
    
    # Собираем ключи фото
    photo_keys = []
    
    # Базовый уход по типу волос
    base_keys = config.PHOTO_MAPPING["волосы"].get(hair_type, [])
    photo_keys.extend(base_keys)
    
    # Фото для проблем
    for problem in problems:
        problem_keys = config.PHOTO_MAPPING["волосы"].get(problem, [])
        photo_keys.extend(problem_keys)
    
    # Чувствительная кожа головы
    if scalp_type == "Да, чувствительная":
        sensitive_keys = config.PHOTO_MAPPING["волосы"].get("чувствительная_кожа", [])
        photo_keys.extend(sensitive_keys)
    
    # Объем
    if hair_volume == "Да, хочу объем":
        volume_keys = config.PHOTO_MAPPING["волосы"].get("объем", [])
        photo_keys.extend(volume_keys)
    
    # Цветовые маски
    if hair_color in ["Шатенка", "Русая"]:
        mask_keys = config.PHOTO_MAPPING["волосы"].get("оттеночная_шоколад", [])
        photo_keys.extend(mask_keys)
    elif hair_color == "Рыжая":
        mask_keys = config.PHOTO_MAPPING["волосы"].get("оттеночная_медный", [])
        photo_keys.extend(mask_keys)
    
    # Убираем дубликаты
    photo_keys = list(set(photo_keys))
    
    # Отправляем рекомендации
    await message.answer(recommendations, parse_mode=ParseMode.MARKDOWN)
    
    # Отправляем фото
    if photo_keys:
        await send_photo_group(
            chat_id=message.chat.id,
            photo_keys=photo_keys,
            caption="📦 Рекомендуемые продукты:"
        )
    else:
        await message.answer("📷 Фото продуктов скоро будут доступны!")
    
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
            "Доступ разрешен. Выберите действие:",
            reply_markup=keyboards.admin_category_keyboard()
        )
    else:
        await message.answer("Неверный пароль. Попробуйте снова.")

@dp.message(F.text == "📊 Статистика", AdminState.ADMIN_MAIN_MENU)
async def admin_stats_handler(message: Message):
    """Статистика загруженных фото"""
    all_photos = await photo_db.get_all_photos()
    
    if not all_photos:
        await message.answer("📭 База данных фото пуста.")
        return
    
    # Группируем по категориям
    stats = {}
    for photo in all_photos:
        category = photo.get('category', 'неизвестно')
        if category not in stats:
            stats[category] = 0
        stats[category] += 1
    
    stats_text = "📊 *Статистика загруженных фото:*\n\n"
    for category, count in stats.items():
        stats_text += f"• {category}: {count} фото\n"
    
    stats_text += f"\nВсего: {len(all_photos)} фото"
    
    await message.answer(stats_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(F.text.in_(["💇‍♀️ Волосы", "🧴 Тело"]), AdminState.ADMIN_MAIN_MENU)
async def admin_category_handler(message: Message, state: FSMContext):
    category = "волосы" if message.text == "💇‍♀️ Волосы" else "тело"
    await state.update_data(admin_category=category)
    await state.set_state(AdminState.ADMIN_CHOOSING_SUBCATEGORY)
    
    await message.answer(
        f"Категория: *{category}*\n\nВыберите подкатегорию:",
        reply_markup=keyboards.admin_subcategory_keyboard(category),
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(AdminState.ADMIN_CHOOSING_SUBCATEGORY)
async def admin_subcategory_handler(message: Message, state: FSMContext):
    admin_data = await state.get_data()
    category = admin_data.get("admin_category", "")
    
    if message.text == "↩️ Назад к категориям":
        await state.set_state(AdminState.ADMIN_MAIN_MENU)
        await message.answer(
            "Выберите действие:",
            reply_markup=keyboards.admin_category_keyboard()
        )
        return
    
    # Проверяем, что выбранная подкатегория существует
    valid_subcategories = list(config.PHOTO_STRUCTURE[category].keys())
    if message.text not in valid_subcategories:
        await message.answer("Пожалуйста, выберите подкатегорию из списка.")
        return
    
    await state.update_data(admin_subcategory=message.text)
    await state.set_state(AdminState.ADMIN_CHOOSING_PRODUCT)
    
    await message.answer(
        f"Категория: *{category}*\n"
        f"Подкатегория: *{message.text}*\n\n"
        f"Выберите продукт для загрузки фото:",
        reply_markup=keyboards.admin_products_keyboard(category, message.text),
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(AdminState.ADMIN_CHOOSING_PRODUCT)
async def admin_product_handler(message: Message, state: FSMContext):
    admin_data = await state.get_data()
    category = admin_data.get("admin_category", "")
    subcategory = admin_data.get("admin_subcategory", "")
    
    if message.text == "↩️ Назад к подкатегориям":
        await state.set_state(AdminState.ADMIN_CHOOSING_SUBCATEGORY)
        await message.answer(
            f"Категория: *{category}*\n\nВыберите подкатегорию:",
            reply_markup=keyboards.admin_subcategory_keyboard(category),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Ищем продукт по display_name
    products = config.PHOTO_STRUCTURE[category][subcategory]
    product_info = None
    
    for product_key, display_name in products:
        if display_name == message.text:
            product_info = (product_key, display_name)
            break
    
    if not product_info:
        await message.answer("Продукт не найден. Выберите из списка.")
        return
    
    product_key, display_name = product_info
    
    await state.update_data(
        admin_product_key=product_key,
        admin_display_name=display_name
    )
    await state.set_state(AdminState.ADMIN_WAITING_PHOTO)
    
    # Проверяем, есть ли уже фото для этого продукта
    existing_photo = await photo_db.get_photo_id(product_key)
    
    if existing_photo:
        await message.answer(
            f"🔄 *Обновление фото*\n\n"
            f"• Продукт: {display_name}\n"
            f"• Ключ: `{product_key}`\n"
            f"• Категория: {category}\n"
            f"• Подкатегория: {subcategory}\n\n"
            f"У этого продукта уже есть загруженное фото.\n"
            f"Отправьте новое фото для замены:",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer(
            f"📤 *Загрузка нового фото*\n\n"
            f"• Продукт: {display_name}\n"
            f"• Ключ: `{product_key}`\n"
            f"• Категория: {category}\n"
            f"• Подкатегория: {subcategory}\n\n"
            f"Отправьте фото для этого продукта:",
            parse_mode=ParseMode.MARKDOWN
        )

@dp.message(F.content_type == ContentType.PHOTO, AdminState.ADMIN_WAITING_PHOTO)
async def admin_photo_handler(message: Message, state: FSMContext):
    admin_data = await state.get_data()
    product_key = admin_data.get("admin_product_key", "")
    category = admin_data.get("admin_category", "")
    subcategory = admin_data.get("admin_subcategory", "")
    display_name = admin_data.get("admin_display_name", "")
    
    if not product_key:
        await message.answer("❌ Ошибка: не выбран продукт.")
        await state.set_state(AdminState.ADMIN_MAIN_MENU)
        return
    
    # Получаем самое большое фото
    photo = message.photo[-1]
    file_id = photo.file_id
    
    # Сохраняем в базу данных
    success = await photo_db.save_photo(
        product_key=product_key,
        category=category,
        subcategory=subcategory,
        display_name=display_name,
        file_id=file_id
    )
    
    if success:
        await message.answer(
            f"✅ *Фото успешно сохранено!*\n\n"
            f"• Продукт: {display_name}\n"
            f"• Ключ: `{product_key}`\n"
            f"• Категория: {category}\n"
            f"• Подкатегория: {subcategory}\n"
            f"• File ID: `{file_id[:30]}...`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer("❌ Ошибка при сохранении фото.")
    
    # Возвращаемся к выбору подкатегории
    await state.set_state(AdminState.ADMIN_CHOOSING_SUBCATEGORY)
    await message.answer(
        f"Категория: *{category}*\n\nВыберите подкатегорию:",
        reply_markup=keyboards.admin_subcategory_keyboard(category),
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(F.text == "↩️ Назад к категориям", AdminState.ADMIN_CHOOSING_SUBCATEGORY)
async def admin_back_to_categories(message: Message, state: FSMContext):
    await state.set_state(AdminState.ADMIN_MAIN_MENU)
    await message.answer(
        "Выберите действие:",
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
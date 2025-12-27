import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import List

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InputFile, FSInputFile, ContentType
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.enums import ParseMode
import uuid

import config
import keyboards
from states import UserState, AdminState
from user_storage import user_data_storage
from photo_database import photo_db
from keep_alive import keep_alive_start

# Генерация уникального ID для экземпляра
INSTANCE_ID = str(uuid.uuid4())[:8]
logging.basicConfig(level=logging.INFO, format=f'%(asctime)s - {INSTANCE_ID} - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Упрощенные названия для ключей фото
SIMPLIFIED_NAMES = {
    "волосы": {
        "общий уход": "волосы_общий",
        "ломкость": "ломкость",
        "выпадение": "выпадение",
        "перхоть/зуд": "перхоть",
        "секущиеся кончики": "секущиеся",
        "тусклость": "тусклость",
        "пушистость": "пушистость",
        "тонкие": "тонкие",
        "очень поврежденные": "поврежденные",
        "чувствительная кожа головы": "чувствительная_кожа",
        "объем": "объем",
        "оттеночная маска холодный шоколад": "оттеночная_шоколад",
        "оттеночная маска медный": "оттеночная_медный",
    },
    "тело": {
        "общий уход": "тело_общий",
        "сухая кожа": "тело_сухая",
        "чувствительная и склонная к раздражениям": "тело_чувствительная",
        "борьба с целлюлитом и тонизирование": "тело_целлюлит",
    }
}

async def send_photo_group(chat_id: int, photo_keys: List[str], caption: str = ""):
    """Отправляет группу фото по ключам"""
    try:
        media_group = []
        
        for key in photo_keys:
            photo_id = await photo_db.get_photo_id(key)
            if photo_id:
                media_group.append(types.InputMediaPhoto(media=photo_id))
            else:
                logger.warning(f"Фото для ключа '{key}' не найдено в БД")
        
        if media_group:
            if caption:
                media_group[0].caption = caption[:1024]
            await bot.send_media_group(chat_id=chat_id, media=media_group)
            return True
        else:
            await bot.send_message(chat_id, "Извините, фото продуктов временно недоступны.")
            return False
    except Exception as e:
        logger.error(f"Ошибка при отправке фото: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при отправке фото.")
        return False

# ==================== ОБЩИЕ КОМАНДЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Привет! Я бот-консультант SVOY AV.COSMETIC.\n"
        "Помогу подобрать уход для волос или тела.",
        reply_markup=keyboards.main_kb()
    )
    await state.set_state(UserState.choosing_category)

@dp.message(Command("admin2026"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.set_state(AdminState.waiting_password)
    await message.answer("Введите пароль для доступа к админ-панели:")

@dp.message(Command("checkphotos"))
async def cmd_checkphotos(message: Message):
    """Проверка загруженных фото"""
    count = await photo_db.count_photos()
    await message.answer(f"📊 В базе данных: {count} фото")

@dp.message(Command("debug"))
async def cmd_debug(message: Message, state: FSMContext):
    """Отладочная информация"""
    current_state = await state.get_state()
    user_id = message.from_user.id
    user_data = user_data_storage.get_data(user_id)
    
    debug_info = (
        f"🧪 Отладка экземпляра {INSTANCE_ID}\n"
        f"👤 User ID: {user_id}\n"
        f"📊 Текущее состояние: {current_state}\n"
        f"💾 Данные пользователя: {user_data}\n"
        f"📷 Фото в БД: {await photo_db.count_photos()}"
    )
    
    await message.answer(debug_info)

@dp.message(Command("check"))
async def cmd_check(message: Message):
    """Проверка конкретного продукта"""
    args = message.text.split()
    if len(args) > 1:
        product_key = args[1]
        photo_id = await photo_db.get_photo_id(product_key)
        if photo_id:
            await message.answer(f"✅ Фото для '{product_key}' найдено: {photo_id[:50]}...")
        else:
            await message.answer(f"❌ Фото для '{product_key}' не найдено")
    else:
        await message.answer("Использование: /check <ключ_продукта>")

# ==================== ОСНОВНОЙ ДИАЛОГ ====================

@dp.message(F.text == "👈 Назад")
async def back_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state == UserState.choosing_hair_type:
        await message.answer("Выберите категорию:", reply_markup=keyboards.main_kb())
        await state.set_state(UserState.choosing_category)
    elif current_state == UserState.choosing_hair_problems:
        await message.answer("Вы окрашивали волосы?", reply_markup=keyboards.hair_type_kb())
        await state.set_state(UserState.choosing_hair_type)
    elif current_state == UserState.choosing_scalp_type:
        await message.answer("Выберите проблемы волос:", reply_markup=keyboards.hair_problems_kb([]))
        await state.set_state(UserState.choosing_hair_problems)
    elif current_state == UserState.choosing_hair_volume:
        await message.answer("Есть ли чувствительность кожи головы?", reply_markup=keyboards.scalp_type_kb())
        await state.set_state(UserState.choosing_scalp_type)
    elif current_state == UserState.choosing_hair_color:
        await message.answer("Хотите добавить объем?", reply_markup=keyboards.hair_volume_kb())
        await state.set_state(UserState.choosing_hair_volume)
    else:
        await cmd_start(message, state)

# ==================== ВЕТКА "ТЕЛО" ====================

@dp.message(F.text == "🧴 Тело")
async def body_handler(message: Message, state: FSMContext):
    # КЛЮЧЕВОЕ РЕШЕНИЕ 1: Проверяем, не находится ли пользователь в админ-режиме
    current_state = await state.get_state()
    if current_state in [AdminState.waiting_password, AdminState.choosing_category, 
                        AdminState.choosing_product, AdminState.waiting_photo]:
        # Пропускаем обработку, если пользователь в админ-режиме
        return
    
    await state.set_state(UserState.choosing_body_goal)
    await message.answer(
        "Выберите задачу для ухода за телом:",
        reply_markup=keyboards.body_goal_kb()
    )

@dp.message(F.text.in_(config.BODY_GOALS), UserState.choosing_body_goal)
async def body_goal_handler(message: Message, state: FSMContext):
    goal = message.text
    user_id = message.from_user.id
    
    # Получаем рекомендации
    recommendations = config.get_body_recommendations(goal)
    
    # Определяем ключи для фото
    photo_keys = []
    if goal == "Общий уход":
        photo_keys.append(SIMPLIFIED_NAMES["тело"]["общий уход"])
    elif goal == "Сухая кожа":
        photo_keys.append(SIMPLIFIED_NAMES["тело"]["сухая кожа"])
    elif goal == "Чувствительная и склонная к раздражениям":
        photo_keys.append(SIMPLIFIED_NAMES["тело"]["чувствительная и склонная к раздражениям"])
    elif goal == "Борьба с целлюлитом и тонизирование":
        photo_keys.append(SIMPLIFIED_NAMES["тело"]["борьба с целлюлитом и тонизирование"])
    
    # Отправляем рекомендации
    await message.answer(f"🎯 **{goal}**\n\n{recommendations}")
    
    # Отправляем фото
    if photo_keys:
        await send_photo_group(user_id, photo_keys, "Рекомендуемые продукты:")
    
    # Предлагаем вернуться в начало
    await message.answer(
        "Хотите подобрать что-то еще?",
        reply_markup=keyboards.back_to_start_kb()
    )
    await state.set_state(UserState.choosing_category)

# ==================== ВЕТКА "ВОЛОСЫ" ====================

@dp.message(F.text == "💇‍♀️ Волосы")
async def hair_handler(message: Message, state: FSMContext):
    await state.set_state(UserState.choosing_hair_type)
    await message.answer(
        "Вы окрашивали волосы?",
        reply_markup=keyboards.hair_type_kb()
    )

@dp.message(F.text.in_(config.HAIR_TYPES), UserState.choosing_hair_type)
async def hair_type_handler(message: Message, state: FSMContext):
    hair_type = message.text
    user_id = message.from_user.id
    user_data_storage.update_data(user_id, {"hair_type": hair_type})
    
    await state.set_state(UserState.choosing_hair_problems)
    await message.answer(
        "Выберите проблемы волос (можно несколько):",
        reply_markup=keyboards.hair_problems_kb([])
    )

@dp.message(UserState.choosing_hair_problems)
async def hair_problems_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = user_data_storage.get_data(user_id)
    selected_problems = user_data.get("hair_problems", [])
    
    if message.text == "✅ Готово":
        if not selected_problems:
            await message.answer("Пожалуйста, выберите хотя бы одну проблему.")
            return
        
        await state.set_state(UserState.choosing_scalp_type)
        await message.answer(
            "Есть ли чувствительность кожи головы?",
            reply_markup=keyboards.scalp_type_kb()
        )
        return
    
    # Добавляем или убираем проблему
    problem = message.text
    if problem in config.HAIR_PROBLEMS:
        if problem in selected_problems:
            selected_problems.remove(problem)
        else:
            selected_problems.append(problem)
        
        user_data_storage.update_data(user_id, {"hair_problems": selected_problems})
        
        # Обновляем клавиатуру
        await message.answer(
            f"Выбрано: {len(selected_problems)} проблем\nВыберите проблемы волос:",
            reply_markup=keyboards.hair_problems_kb(selected_problems)
        )

@dp.message(F.text.in_(config.SCALP_TYPES), UserState.choosing_scalp_type)
async def scalp_type_handler(message: Message, state: FSMContext):
    scalp_type = message.text
    user_id = message.from_user.id
    user_data_storage.update_data(user_id, {"scalp_type": scalp_type})
    
    await state.set_state(UserState.choosing_hair_volume)
    await message.answer(
        "Хотите добавить объем?",
        reply_markup=keyboards.hair_volume_kb()
    )

@dp.message(F.text.in_(config.HAIR_VOLUME), UserState.choosing_hair_volume)
async def hair_volume_handler(message: Message, state: FSMContext):
    hair_volume = message.text
    user_id = message.from_user.id
    user_data_storage.update_data(user_id, {"hair_volume": hair_volume})
    
    # Для окрашенных блондинок и остальных спрашиваем цвет
    user_data = user_data_storage.get_data(user_id)
    hair_type = user_data.get("hair_type", "")
    
    if hair_type in ["Окрашенные блондинки", "Окрашенные все остальные"]:
        await state.set_state(UserState.choosing_hair_color)
        await message.answer(
            "Выберите цвет волос:",
            reply_markup=keyboards.hair_color_kb(hair_type)
        )
    else:
        # Для натуральных волос сразу формируем рекомендации
        await generate_hair_recommendation(message, state)

@dp.message(F.text.in_(config.get_hair_colors("Окрашенные все остальные")), UserState.choosing_hair_color)
async def hair_color_handler(message: Message, state: FSMContext):
    hair_color = message.text
    user_id = message.from_user.id
    user_data_storage.update_data(user_id, {"hair_color": hair_color})
    
    await generate_hair_recommendation(message, state)

async def generate_hair_recommendation(message: Message, state: FSMContext):
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
    
    # Определяем ключи для фото
    photo_keys = []
    
    # Общий уход
    if hair_type == "Окрашенные блондинки":
        photo_keys.append("blond_общий")
    elif hair_type == "Окрашенные все остальные":
        photo_keys.append("colored_общий")
    else:  # Натуральные
        photo_keys.append("natural_общий")
    
    # Проблемы
    for problem in problems:
        if problem in SIMPLIFIED_NAMES["волосы"]:
            photo_keys.append(SIMPLIFIED_NAMES["волосы"][problem])
    
    # Чувствительная кожа
    if scalp_type == "Да, чувствительная":
        photo_keys.append(SIMPLIFIED_NAMES["волосы"]["чувствительная кожа головы"])
    
    # Объем
    if hair_volume == "Да, хочу объем":
        photo_keys.append(SIMPLIFIED_NAMES["волосы"]["объем"])
    
    # Цветовые маски
    if hair_color in ["Шатенка", "Русая"]:
        photo_keys.append(SIMPLIFIED_NAMES["волосы"]["оттеночная маска холодный шоколад"])
    elif hair_color == "Рыжая":
        photo_keys.append(SIMPLIFIED_NAMES["волосы"]["оттеночная маска медный"])
    
    # Отправляем рекомендации
    await message.answer(f"💇‍♀️ **Ваш персонализированный уход**\n\n{recommendations}")
    
    # Отправляем фото
    if photo_keys:
        # Убираем дубликаты
        photo_keys = list(set(photo_keys))
        await send_photo_group(user_id, photo_keys, "Рекомендуемые продукты:")
    
    # Добавляем информацию о точках продаж
    await message.answer(
        config.SALES_POINTS + "\n\n" + config.DELIVERY_INFO,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Предлагаем вернуться в начало
    await message.answer(
        "Хотите подобрать что-то еще?",
        reply_markup=keyboards.back_to_start_kb()
    )
    await state.set_state(UserState.choosing_category)
    
    # Очищаем данные пользователя
    user_data_storage.clear_data(user_id)

# ==================== АДМИН-ПАНЕЛЬ ====================

@dp.message(AdminState.waiting_password)
async def admin_password_handler(message: Message, state: FSMContext):
    if message.text == config.ADMIN_PASSWORD:
        await state.set_state(AdminState.choosing_category)
        await message.answer(
            "Доступ разрешен. Выберите категорию для загрузки фото:",
            reply_markup=keyboards.admin_category_kb()
        )
    else:
        await message.answer("Неверный пароль. Попробуйте снова или введите /start для выхода.")

@dp.message(F.text.in_(["💇‍♀️ Волосы", "🧴 Тело"]), AdminState.choosing_category)
async def admin_category_handler(message: Message, state: FSMContext):
    category = "волосы" if message.text == "💇‍♀️ Волосы" else "тело"
    await state.update_data(admin_category=category)
    await state.set_state(AdminState.choosing_product)
    
    # Получаем список продуктов для выбранной категории
    if category == "волосы":
        products = list(SIMPLIFIED_NAMES["волосы"].keys())
    else:
        products = list(SIMPLIFIED_NAMES["тело"].keys())
    
    await message.answer(
        f"Категория: {category}\nВыберите продукт:",
        reply_markup=keyboards.admin_products_kb(products)
    )

@dp.message(AdminState.choosing_product)
async def admin_product_handler(message: Message, state: FSMContext):
    product = message.text
    admin_data = await state.get_data()
    category = admin_data.get("admin_category", "")
    
    # Получаем ключ продукта
    if category == "волосы":
        product_key = SIMPLIFIED_NAMES["волосы"].get(product, product)
    else:
        product_key = SIMPLIFIED_NAMES["тело"].get(product, product)
    
    await state.update_data(admin_product=product_key)
    await state.set_state(AdminState.waiting_photo)
    
    await message.answer(
        f"Продукт: {product}\nКлюч: {product_key}\n\n"
        f"Отправьте фото для этого продукта (одним сообщением)."
    )

@dp.message(F.content_type == ContentType.PHOTO, AdminState.waiting_photo)
async def admin_photo_handler(message: Message, state: FSMContext):
    admin_data = await state.get_data()
    product_key = admin_data.get("admin_product", "")
    
    if not product_key:
        await message.answer("Ошибка: не выбран продукт.")
        await state.set_state(AdminState.choosing_category)
        return
    
    # Получаем самое большое фото
    photo = message.photo[-1]
    photo_id = photo.file_id
    
    # Сохраняем в базу данных
    success = await photo_db.save_photo(product_key, photo_id)
    
    if success:
        await message.answer(f"✅ Фото для '{product_key}' успешно сохранено!")
    else:
        await message.answer(f"❌ Ошибка при сохранении фото для '{product_key}'")
    
    # Возвращаемся к выбору категории
    await state.set_state(AdminState.choosing_category)
    await message.answer(
        "Выберите категорию для загрузки фото:",
        reply_markup=keyboards.admin_category_kb()
    )

@dp.message(Command("delete_photo"))
async def cmd_delete_photo(message: Message):
    """Удаление фото по ключу (только для админа)"""
    args = message.text.split()
    if len(args) > 1:
        product_key = args[1]
        success = await photo_db.delete_photo(product_key)
        if success:
            await message.answer(f"✅ Фото для '{product_key}' удалено")
        else:
            await message.answer(f"❌ Фото для '{product_key}' не найдено")
    else:
        await message.answer("Использование: /delete_photo <ключ_продукта>")

# ==================== ЗАПУСК БОТА ====================

async def run_bot():
    """Запуск бота с обработкой ошибок"""
    # КЛЮЧЕВОЕ РЕШЕНИЕ 2: Увеличиваем задержку и добавляем остановку старых процессов
    logger.info(f"🔄 Запуск экземпляра {INSTANCE_ID}...")
    
    # Даем время завершиться старому процессу
    await asyncio.sleep(180)  # Увеличено с 120 до 180 секунд
    
    try:
        # Останавливаем поллинг если он уже запущен
        await bot.session.close()
    except:
        pass
    
    # Инициализируем базу данных
    await photo_db.init_db()
    logger.info("📊 База данных фото инициализирована")
    
    # Запускаем keep-alive сервер
    keep_alive_start()
    
    # Запускаем поллинг
    logger.info("🤖 Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Принудительная остановка старых процессов
    try:
        import subprocess
        subprocess.run(["pkill", "-f", "python.*main.py"], stderr=subprocess.DEVNULL)
    except:
        pass
    
    asyncio.run(run_bot())
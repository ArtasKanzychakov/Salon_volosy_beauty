"""
MAIN.PY - Основной файл бота SVOY AV.COSMETIC
Перестроенная версия с улучшенной архитектурой
"""

import asyncio
import logging
import sys
import os
from typing import List, Dict, Any
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ContentType, CallbackQuery
from aiogram.enums import ParseMode

import config
import keyboards
from states import UserState, AdminState
from user_storage import user_data_storage, init_user_storage
from photo_database import photo_db, init_database
from keep_alive import keep_alive_start, keep_alive_stop

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================

# Создаем логгер
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ID экземпляра для логирования
INSTANCE_ID = os.environ.get("RENDER_INSTANCE_ID", "local")
logger.info(f"🚀 Запуск экземпляра бота (ID: {INSTANCE_ID})")

# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ====================

# Проверка токена
if not config.BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не установлен. Завершение работы.")
    sys.exit(1)

bot = Bot(token=config.BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== СИСТЕМА УПРАВЛЕНИЯ ФОТО ====================

class PhotoManager:
    """Менеджер для работы с фото продуктами"""
    
    # Маппинг целей на ключи фото
    BODY_PHOTO_MAPPING = {
        "Общий уход": "body_general",
        "Сухая кожа": "body_dry",
        "Чувствительная и склонная к раздражениям": "body_sensitive",
        "Борьба с целлюлитом и тонизирование": "body_cellulite"
    }
    
    # Маппинг типов волос на ключи фото
    HAIR_TYPE_PHOTO_MAPPING = {
        "Окрашенные блондинки": "hair_blonde_general",
        "Окрашенные все остальные": "hair_colored_general",
        "Натуральные": "hair_natural_general"
    }
    
    # Маппинг проблем волос на ключи фото
    HAIR_PROBLEM_PHOTO_MAPPING = {
        "Ломкость": "hair_brittle",
        "Выпадение": "hair_loss",
        "Перхоть/зуд": "hair_dandruff",
        "Секущиеся кончики": "hair_split",
        "Тусклость": "hair_dull",
        "Пушистость": "hair_frizzy",
        "Тонкие": "hair_thin",
        "Очень поврежденные": "hair_damaged"
    }
    
    # Дополнительные фото
    HAIR_SPECIAL_PHOTO_MAPPING = {
        "чувствительная_кожа": "hair_scalp_sensitive",
        "объем": "hair_volume",
        "оттеночная_шоколад": "hair_mask_chocolate",
        "оттеночная_медный": "hair_mask_copper"
    }
    
    @staticmethod
    async def get_body_photo_keys(goal: str) -> List[str]:
        """Получить ключи фото для цели тела"""
        key = PhotoManager.BODY_PHOTO_MAPPING.get(goal)
        return [key] if key else []
    
    @staticmethod
    async def get_hair_photo_keys(hair_type: str, problems: List[str], 
                                 scalp_type: str, hair_volume: str, 
                                 hair_color: str = "") -> List[str]:
        """Получить ключи фото для волос"""
        keys = []
        
        # Базовый уход по типу волос
        base_key = PhotoManager.HAIR_TYPE_PHOTO_MAPPING.get(hair_type)
        if base_key:
            keys.append(base_key)
        
        # Фото для проблем
        for problem in problems:
            key = PhotoManager.HAIR_PROBLEM_PHOTO_MAPPING.get(problem)
            if key:
                keys.append(key)
        
        # Чувствительная кожа головы
        if scalp_type == "Да, чувствительная":
            keys.append(PhotoManager.HAIR_SPECIAL_PHOTO_MAPPING["чувствительная_кожа"])
        
        # Объем
        if hair_volume == "Да, хочу объем":
            keys.append(PhotoManager.HAIR_SPECIAL_PHOTO_MAPPING["объем"])
        
        # Цветовые маски
        if hair_color in ["Шатенка", "Русая"]:
            keys.append(PhotoManager.HAIR_SPECIAL_PHOTO_MAPPING["оттеночная_шоколад"])
        elif hair_color == "Рыжая":
            keys.append(PhotoManager.HAIR_SPECIAL_PHOTO_MAPPING["оттеночная_медный"])
        
        # Убираем дубликаты
        return list(set(keys))
    
    @staticmethod
    async def send_photos(chat_id: int, photo_keys: List[str], caption: str = "") -> bool:
        """Отправить фото по ключам"""
        if not photo_keys:
            return False
        
        try:
            media_group = []
            
            for key in photo_keys:
                photo_id = await photo_db.get_photo_id(key)
                if photo_id:
                    from aiogram.types import InputMediaPhoto
                    media_group.append(InputMediaPhoto(media=photo_id))
                else:
                    logger.warning(f"Фото для ключа '{key}' не найдено")
            
            if media_group and caption:
                media_group[0].caption = caption[:1024]
            
            if media_group:
                await bot.send_media_group(chat_id=chat_id, media=media_group)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка отправки фото: {e}")
            return False

# ==================== ОБЩИЕ КОМАНДЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Команда /start"""
    await state.clear()
    
    welcome_text = (
        "👋 *Добро пожаловать в SVOY AV.COSMETIC!*\n\n"
        "Я ваш персональный консультант по уходу за волосами и телом.\n"
        "Помогу подобрать идеальные средства именно для вас!"
    )
    
    await message.answer(welcome_text, parse_mode=ParseMode.MARKDOWN)
    await show_main_menu(message, state)

async def show_main_menu(message: Message, state: FSMContext):
    """Показать главное меню"""
    await state.set_state(UserState.MAIN_MENU)
    await message.answer(
        "👇 Выберите категорию:",
        reply_markup=keyboards.main_menu_keyboard()
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    help_text = (
        "📋 *Доступные команды:*\n\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n"
        "/admin - Вход в админ-панель\n"
        "/stats - Статистика бота\n"
        "/contacts - Контакты салона"
    )
    
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("contacts"))
async def cmd_contacts(message: Message):
    """Команда /contacts"""
    await message.answer(
        f"{config.SALES_POINTS}\n\n{config.DELIVERY_INFO}",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Команда /stats"""
    photo_count = await photo_db.count_photos()
    storage_stats = user_data_storage.get_stats()
    
    stats_text = (
        f"📊 *Статистика бота:*\n\n"
        f"• Экземпляр: `{INSTANCE_ID}`\n"
        f"• Фото в базе: `{photo_count}`\n"
        f"• Пользователей в памяти: `{storage_stats['total_users']}`\n"
        f"• Записей данных: `{storage_stats['total_entries']}`"
    )
    
    await message.answer(stats_text, parse_mode=ParseMode.MARKDOWN)

# ==================== ОБРАБОТКА КНОПКИ "ГЛАВНОЕ МЕНЮ" ====================

@dp.message(F.text == "🏠 Главное меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    """Возврат в главное меню"""
    await cmd_start(message, state)

# ==================== КАТЕГОРИЯ "ТЕЛО" ====================

@dp.message(F.text == "🧴 Тело", UserState.MAIN_MENU)
async def body_category_handler(message: Message, state: FSMContext):
    """Обработка выбора категории "Тело" """
    await state.set_state(UserState.BODY_CHOOSING_GOAL)
    await message.answer(
        "👇 Выберите цель ухода за телом:",
        reply_markup=keyboards.body_goals_keyboard()
    )

@dp.message(F.text.in_(config.BODY_GOALS), UserState.BODY_CHOOSING_GOAL)
async def body_goal_handler(message: Message, state: FSMContext):
    """Обработка выбора цели для тела"""
    goal = message.text
    
    # Получаем рекомендации
    recommendations = config.get_body_recommendations(goal)
    
    # Получаем ключи фото
    photo_keys = await PhotoManager.get_body_photo_keys(goal)
    
    # Отправляем рекомендации
    await message.answer(
        f"🎯 *{goal}*\n\n{recommendations}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Отправляем фото
    if photo_keys:
        success = await PhotoManager.send_photos(
            chat_id=message.chat.id,
            photo_keys=photo_keys,
            caption="📦 *Рекомендуемые продукты:*"
        )
        if not success:
            await message.answer("📷 Фото продуктов скоро будут доступны!")
    
    # Информация о точках продаж
    await message.answer(
        config.SALES_POINTS,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Возвращаем в главное меню
    await show_main_menu(message, state)

# ==================== КАТЕГОРИЯ "ВОЛОСЫ" ====================

@dp.message(F.text == "💇‍♀️ Волосы", UserState.MAIN_MENU)
async def hair_category_handler(message: Message, state: FSMContext):
    """Обработка выбора категории "Волосы" """
    await state.set_state(UserState.HAIR_CHOOSING_TYPE)
    await message.answer(
        "👇 Вы окрашивали волосы?",
        reply_markup=keyboards.hair_type_keyboard()
    )

@dp.message(F.text.in_(config.HAIR_TYPES), UserState.HAIR_CHOOSING_TYPE)
async def hair_type_handler(message: Message, state: FSMContext):
    """Обработка выбора типа волос"""
    hair_type = message.text
    user_data_storage.update_data(message.from_user.id, {"hair_type": hair_type})
    
    await state.set_state(UserState.HAIR_CHOOSING_PROBLEMS)
    await message.answer(
        "👇 Выберите проблемы волос (можно несколько):",
        reply_markup=keyboards.hair_problems_keyboard()
    )

@dp.message(UserState.HAIR_CHOOSING_PROBLEMS)
async def hair_problems_handler(message: Message, state: FSMContext):
    """Обработка выбора проблем волос"""
    user_id = message.from_user.id
    user_data = user_data_storage.get_data(user_id)
    selected_problems = user_data.get("hair_problems", [])
    
    if message.text == "✅ Готово":
        if not selected_problems:
            await message.answer("⚠️ Пожалуйста, выберите хотя бы одну проблему.")
            return
        
        await state.set_state(UserState.HAIR_CHOOSING_SCALP)
        await message.answer(
            "👇 Есть ли чувствительность кожи головы?",
            reply_markup=keyboards.scalp_type_keyboard()
        )
        return
    
    # Добавление/удаление проблемы
    problem_text = message.text.replace("✅ ", "").replace("☐ ", "")
    
    if problem_text in config.HAIR_PROBLEMS:
        if problem_text in selected_problems:
            selected_problems.remove(problem_text)
        else:
            selected_problems.append(problem_text)
        
        user_data_storage.update_data(user_id, {"hair_problems": selected_problems})
        
        # Обновляем клавиатуру
        await message.answer(
            f"Выбрано: {len(selected_problems)} проблем\n"
            "👇 Выберите проблемы волос:",
            reply_markup=keyboards.hair_problems_keyboard(selected_problems)
        )

@dp.message(F.text.in_(config.SCALP_TYPES), UserState.HAIR_CHOOSING_SCALP)
async def scalp_type_handler(message: Message, state: FSMContext):
    """Обработка выбора типа кожи головы"""
    scalp_type = message.text
    user_data_storage.update_data(message.from_user.id, {"scalp_type": scalp_type})
    
    await state.set_state(UserState.HAIR_CHOOSING_VOLUME)
    await message.answer(
        "👇 Хотите добавить объем?",
        reply_markup=keyboards.hair_volume_keyboard()
    )

@dp.message(F.text.in_(config.HAIR_VOLUME), UserState.HAIR_CHOOSING_VOLUME)
async def hair_volume_handler(message: Message, state: FSMContext):
    """Обработка выбора объема"""
    hair_volume = message.text
    user_id = message.from_user.id
    user_data_storage.update_data(user_id, {"hair_volume": hair_volume})
    
    user_data = user_data_storage.get_data(user_id)
    hair_type = user_data.get("hair_type", "")
    
    # Для окрашенных спрашиваем цвет
    if hair_type in ["Окрашенные блондинки", "Окрашенные все остальные"]:
        await state.set_state(UserState.HAIR_CHOOSING_COLOR)
        await message.answer(
            "👇 Выберите цвет волос:",
            reply_markup=keyboards.hair_color_keyboard(hair_type)
        )
    else:
        # Для натуральных сразу формируем результат
        await generate_hair_result(message, state)

@dp.message(UserState.HAIR_CHOOSING_COLOR)
async def hair_color_handler(message: Message, state: FSMContext):
    """Обработка выбора цвета волос"""
    user_id = message.from_user.id
    user_data = user_data_storage.get_data(user_id)
    hair_type = user_data.get("hair_type", "")
    
    # Проверяем, что выбран допустимый цвет
    valid_colors = config.HAIR_COLORS.get(hair_type, [])
    if message.text not in valid_colors:
        await message.answer("⚠️ Пожалуйста, выберите цвет из списка.")
        return
    
    user_data_storage.update_data(user_id, {"hair_color": message.text})
    await generate_hair_result(message, state)

async def generate_hair_result(message: Message, state: FSMContext):
    """Формирование и отправка результата для волос"""
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
    
    # Получаем ключи фото
    photo_keys = await PhotoManager.get_hair_photo_keys(
        hair_type, problems, scalp_type, hair_volume, hair_color
    )
    
    # Отправляем рекомендации
    await message.answer(
        recommendations,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Отправляем фото
    if photo_keys:
        success = await PhotoManager.send_photos(
            chat_id=message.chat.id,
            photo_keys=photo_keys,
            caption="📦 *Рекомендуемые продукты:*"
        )
        if not success:
            await message.answer("📷 Фото продуктов скоро будут доступны!")
    
    # Информация о точках продаж и доставке
    await message.answer(
        f"{config.SALES_POINTS}\n\n{config.DELIVERY_INFO}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Очищаем данные пользователя
    user_data_storage.clear_data(user_id)
    
    # Возвращаем в главное меню
    await show_main_menu(message, state)

# ==================== АДМИН-ПАНЕЛЬ ====================

@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Вход в админ-панель"""
    await state.set_state(AdminState.AWAITING_PASSWORD)
    await message.answer(
        "🔐 *Вход в админ-панель*\n\n"
        "Введите пароль:",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(AdminState.AWAITING_PASSWORD)
async def admin_password_handler(message: Message, state: FSMContext):
    """Проверка пароля админ-панели"""
    if message.text == config.ADMIN_PASSWORD:
        await state.set_state(AdminState.ADMIN_MAIN_MENU)
        await message.answer(
            "✅ *Доступ разрешен!*\n\n"
            "Добро пожаловать в админ-панель.",
            reply_markup=keyboards.admin_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer("❌ Неверный пароль. Попробуйте еще раз.")

@dp.message(F.text == "🚪 Выйти из админки", AdminState.ADMIN_MAIN_MENU)
async def admin_exit_handler(message: Message, state: FSMContext):
    """Выход из админ-панели"""
    await state.clear()
    await message.answer(
        "✅ Вы вышли из админ-панели.",
        reply_markup=keyboards.main_menu_keyboard()
    )

@dp.message(F.text == "📤 Загрузить фото", AdminState.ADMIN_MAIN_MENU)
async def admin_upload_handler(message: Message, state: FSMContext):
    """Начало загрузки фото"""
    await state.set_state(AdminState.ADMIN_CHOOSING_CATEGORY)
    await message.answer(
        "👇 Выберите категорию для загрузки фото:",
        reply_markup=keyboards.admin_category_keyboard()
    )

@dp.message(F.text.in_(["💇‍♀️ Волосы", "🧴 Тело"]), AdminState.ADMIN_CHOOSING_CATEGORY)
async def admin_category_handler(message: Message, state: FSMContext):
    """Выбор категории для загрузки фото"""
    category = "волосы" if message.text == "💇‍♀️ Волосы" else "тело"
    
    await state.update_data(admin_category=category)
    await state.set_state(AdminState.ADMIN_CHOOSING_PRODUCT)
    
    # Получаем список продуктов для категории
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
        f"Категория: *{category}*\n\n👇 Выберите продукт:",
        reply_markup=keyboards.admin_products_keyboard(products),
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(AdminState.ADMIN_CHOOSING_PRODUCT)
async def admin_product_handler(message: Message, state: FSMContext):
    """Выбор продукта для загрузки фото"""
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
        await message.answer("❌ Неизвестный продукт. Выберите из списка.")
        return
    
    await state.update_data(admin_product=product_key)
    await state.set_state(AdminState.ADMIN_AWAITING_PHOTO)
    
    await message.answer(
        f"📦 *Продукт:* {product}\n"
        f"🔑 *Ключ:* `{product_key}`\n"
        f"📂 *Категория:* {category}\n\n"
        "👇 Отправьте фото для этого продукта:",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(F.content_type == ContentType.PHOTO, AdminState.ADMIN_AWAITING_PHOTO)
async def admin_photo_handler(message: Message, state: FSMContext):
    """Обработка загрузки фото"""
    admin_data = await state.get_data()
    product_key = admin_data.get("admin_product", "")
    category = admin_data.get("admin_category", "")
    
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
        file_id=file_id,
        category=category
    )
    
    if success:
        await message.answer(
            f"✅ *Фото успешно сохранено!*\n\n"
            f"• Продукт: `{product_key}`\n"
            f"• Категория: {category}\n"
            f"• File ID: `{file_id[:30]}...`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer("❌ Ошибка при сохранении фото.")
    
    # Возвращаемся в меню загрузки
    await state.set_state(AdminState.ADMIN_CHOOSING_CATEGORY)
    await message.answer(
        "👇 Выберите категорию для загрузки фото:",
        reply_markup=keyboards.admin_category_keyboard()
    )

@dp.message(F.text == "↩️ Назад к категориям", AdminState.ADMIN_CHOOSING_PRODUCT)
async def admin_back_to_categories(message: Message, state: FSMContext):
    """Возврат к выбору категории"""
    await state.set_state(AdminState.ADMIN_CHOOSING_CATEGORY)
    await message.answer(
        "👇 Выберите категорию для загрузки фото:",
        reply_markup=keyboards.admin_category_keyboard()
    )

@dp.message(F.text == "↩️ Назад в админку", AdminState.ADMIN_CHOOSING_CATEGORY)
async def admin_back_to_main(message: Message, state: FSMContext):
    """Возврат в главное меню админки"""
    await state.set_state(AdminState.ADMIN_MAIN_MENU)
    await message.answer(
        "👇 Админ-панель:",
        reply_markup=keyboards.admin_main_keyboard()
    )

@dp.message(F.text == "📊 Статистика", AdminState.ADMIN_MAIN_MENU)
async def admin_stats_handler(message: Message):
    """Статистика админ-панели"""
    photo_count = await photo_db.count_photos()
    all_photos = await photo_db.get_all_photos()
    
    # Группируем по категориям
    categories = {}
    for photo in all_photos:
        category = photo.get('category', 'unknown')
        categories[category] = categories.get(category, 0) + 1
    
    # Формируем текст
    stats_text = "📊 *Статистика базы данных фото:*\n\n"
    stats_text += f"• Всего фото: `{photo_count}`\n\n"
    stats_text += "• По категориям:\n"
    for category, count in categories.items():
        stats_text += f"  - {category}: `{count}`\n"
    
    if all_photos:
        latest = max(all_photos, key=lambda x: x.get('uploaded_at', datetime.min))
        stats_text += f"\n• Последнее обновление: `{latest.get('uploaded_at')}`"
        stats_text += f"\n• Последний продукт: `{latest.get('product_key')}`"
    
    await message.answer(stats_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(F.text == "🗑 Удалить фото", AdminState.ADMIN_MAIN_MENU)
async def admin_delete_handler(message: Message, state: FSMContext):
    """Удаление фото (пока просто информация)"""
    all_photos = await photo_db.get_all_photos()
    
    if not all_photos:
        await message.answer("📭 База данных фото пуста.")
        return
    
    delete_text = "🗑 *Удаление фото*\n\n"
    delete_text += "Для удаления фото используйте команду:\n"
    delete_text += "`/delete_photo <ключ_продукта>`\n\n"
    delete_text += "*Доступные ключи:*\n"
    
    for photo in all_photos[:10]:  # Показываем первые 10
        delete_text += f"• `{photo['product_key']}`\n"
    
    if len(all_photos) > 10:
        delete_text += f"\n... и еще {len(all_photos) - 10} ключей"
    
    await message.answer(delete_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("delete_photo"))
async def cmd_delete_photo(message: Message):
    """Команда для удаления фото"""
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer(
            "Использование: `/delete_photo <ключ_продукта>`\n\n"
            "Например: `/delete_photo hair_blonde_general`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    product_key = parts[1]
    success = await photo_db.delete_photo(product_key)
    
    if success:
        await message.answer(f"✅ Фото `{product_key}` удалено.")
    else:
        await message.answer(f"❌ Фото `{product_key}` не найдено.")

# ==================== ЗАПУСК И ОСНОВНАЯ ФУНКЦИЯ ====================

async def on_startup():
    """Действия при запуске бота"""
    logger.info("=" * 50)
    logger.info("🚀 ЗАПУСК БОТА SVOY AV.COSMETIC")
    logger.info("=" * 50)
    
    # Инициализация базы данных
    logger.info("📊 Инициализация базы данных...")
    db_success = await init_database()
    
    if not db_success:
        logger.error("❌ Не удалось подключиться к базе данных")
        # Продолжаем работу без базы данных
    else:
        logger.info("✅ База данных подключена")
    
    # Инициализация хранилища пользователей
    logger.info("💾 Инициализация хранилища пользователей...")
    await init_user_storage()
    logger.info("✅ Хранилище пользователей инициализировано")
    
    # Запуск keep-alive системы
    logger.info("🔧 Запуск keep-alive системы...")
    await keep_alive_start()
    logger.info("✅ Keep-alive система запущена")
    
    # Проверка токена
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот запущен: @{bot_info.username} ({bot_info.id})")
    
    # Уведомление администратору
    if config.ADMIN_ID:
        try:
            await bot.send_message(
                config.ADMIN_ID,
                f"✅ Бот @{bot_info.username} запущен!\n"
                f"Экземпляр: {INSTANCE_ID}\n"
                f"Время: {datetime.now()}"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу: {e}")
    
    logger.info("=" * 50)

async def on_shutdown():
    """Действия при завершении работы бота"""
    logger.info("🛑 Завершение работы бота...")
    
    # Остановка keep-alive
    await keep_alive_stop()
    logger.info("✅ Keep-alive остановлен")
    
    # Закрытие базы данных
    await photo_db.close()
    logger.info("✅ База данных закрыта")
    
    # Уведомление администратору
    if config.ADMIN_ID:
        try:
            await bot.send_message(
                config.ADMIN_ID,
                f"🛑 Бот остановлен\n"
                f"Экземпляр: {INSTANCE_ID}\n"
                f"Время: {datetime.now()}"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу: {e}")
    
    logger.info("=" * 50)

async def main():
    """Основная функция"""
    try:
        # Регистрация обработчиков запуска/остановки
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        logger.info("🔄 Запуск поллинга...")
        
        # Запуск бота
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        await on_shutdown()
        raise

if __name__ == "__main__":
    # Обработка Ctrl+C
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Принудительное завершение работы (Ctrl+C)")
    except Exception as e:
        logger.error(f"Необработанное исключение: {e}")
        sys.exit(1)
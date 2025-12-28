"""
MAIN.PY - Главный файл бота SVOY AV.COSMETIC
Исправленная версия с корректной работой БД и возможностью делать несколько подборок
"""

import os
import logging
import asyncio
import aiohttp
from datetime import datetime
import schedule
import time
from threading import Thread
from typing import List

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

import config
from states import UserState, AdminState
import keyboards
from photo_database import photo_db

# Импорт user_storage
from user_storage import (
    save_user_data,
    get_user_data_value,
    add_selected_problem,
    remove_selected_problem,
    get_selected_problems,
    clear_selected_problems,
    delete_user_data
)

# Импорт keep_alive
try:
    from keep_alive import keep_alive
    KEEP_ALIVE_AVAILABLE = True
except ImportError:
    KEEP_ALIVE_AVAILABLE = False
    print("⚠️ Модуль keep_alive не найден. Health check не будет работать.")

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Проверка токена
if not config.BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не установлен в config.py или переменных окружения!")

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Глобальная переменная для self-ping
APP_URL = None

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def new_selection_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для новой подборки"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔄 Новая подборка"))
    builder.add(KeyboardButton(text="🏠 Главное меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def final_menu_keyboard() -> ReplyKeyboardMarkup:
    """Финальное меню после рекомендаций"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔄 Новая подборка"))
    builder.add(KeyboardButton(text="💇‍♀️ Волосы"))
    builder.add(KeyboardButton(text="🧴 Тело"))
    builder.add(KeyboardButton(text="🏠 Главное меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

async def send_recommended_photos(chat_id: int, photo_keys: List[str], caption: str = ""):
    """Отправка рекомендованных фото"""
    try:
        if not photo_keys:
            await bot.send_message(
                chat_id, 
                "📷 Фото продуктов для этих рекомендаций пока не загружены.",
                reply_markup=final_menu_keyboard()
            )
            return

        # Проверяем состояние БД
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
                # Находим отображаемое имя
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
                await asyncio.sleep(0.5)  # Задержка между отправками

        if sent_count == 0:
            await bot.send_message(
                chat_id,
                "📷 Фото продуктов временно недоступны. \n\n"
                "Администратор еще не загрузил фотографии для этих продуктов.",
                reply_markup=final_menu_keyboard()
            )

    except Exception as e:
        logger.error(f"❌ Ошибка при отправке фото: {e}")
        await bot.send_message(
            chat_id,
            "❌ Произошла ошибка при отправке фото.",
            reply_markup=final_menu_keyboard()
        )

async def get_body_recommendations_with_photos(goal: str) -> tuple:
    """Получение рекомендаций для тела с фото"""
    try:
        # Получаем текстовые рекомендации
        if goal in config.BODY_DATA:
            data = config.BODY_DATA[goal]
            text = f"{data['title']}\n\n"
            for product in data['products']:
                text += f"• {product}\n"
            if 'note' in data:
                text += f"\n{data['note']}"
        else:
            text = config.get_body_recommendations_html(goal)

        # Получаем ключи фото для этой цели
        photo_keys = config.PHOTO_MAPPING.get("тело", {}).get(goal, [])

        return text, photo_keys

    except Exception as e:
        logger.error(f"❌ Ошибка получения рекомендаций для тела: {e}")
        return "Рекомендации временно недоступны.", []

async def get_hair_recommendations_with_photos(hair_type: str, problems: list, 
                                              scalp_type: str, hair_volume: str, 
                                              hair_color: str = "") -> tuple:
    """Получение рекомендаций для волос с фото"""
    try:
        # Получаем текстовые рекомендации
        text = config.get_hair_recommendations_html(hair_type, problems, scalp_type, hair_volume, hair_color)

        # Собираем ключи фото
        photo_keys = []

        # Базовый уход по типу волос
        if hair_type in config.PHOTO_MAPPING.get("волосы", {}):
            photo_keys.extend(config.PHOTO_MAPPING["волосы"][hair_type])

        # Фото для проблем
        for problem in problems:
            if problem in config.PHOTO_MAPPING.get("волосы", {}):
                photo_keys.extend(config.PHOTO_MAPPING["волосы"][problem])

        # Дополнительные фото
        if scalp_type == "Да, чувствительная":
            sensitive_keys = config.PHOTO_MAPPING["волосы"].get("чувствительная_кожа", [])
            photo_keys.extend(sensitive_keys)

        if hair_volume == "Да, хочу объем":
            volume_keys = config.PHOTO_MAPPING["волосы"].get("объем", [])
            photo_keys.extend(volume_keys)

        if hair_color in ["Шатенка", "Русая"]:
            chocolate_keys = config.PHOTO_MAPPING["волосы"].get("оттеночная_шоколад", [])
            photo_keys.extend(chocolate_keys)
        elif hair_color == "Рыжая":
            copper_keys = config.PHOTO_MAPPING["волосы"].get("оттеночная_медный", [])
            photo_keys.extend(copper_keys)

        # Убираем дубликаты
        photo_keys = list(set(photo_keys))

        return text, photo_keys

    except Exception as e:
        logger.error(f"❌ Ошибка получения рекомендаций для волос: {e}")
        return "Рекомендации временно недоступны.", []

# ==================== МИДЛВЕЙР ДЛЯ ПРОВЕРКИ БД ====================

@dp.update.middleware()
async def check_db_middleware(handler, event, data):
    """Проверка состояния БД перед обработкой"""
    if not photo_db.is_connected:
        logger.warning("⚠️ БД не подключена, пытаемся переподключиться...")
        await photo_db.init_db()

    return await handler(event, data)

# ==================== КОМАНДЫ БОТА ====================

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    try:
        await state.clear()
        delete_user_data(message.from_user.id)

        welcome_text = (
            "👋 <b>Добро пожаловать в SVOY AV.COSMETIC!</b>\n\n"
            "Я помогу подобрать идеальную косметику для:\n"
            "💇‍♀️ <b>Волос</b> — подбор по типу, проблемам и цвету\n"
            "🧴 <b>Тело</b> — уход по потребностям кожи\n\n"
            "<i>Выберите категорию:</i>"
        )

        await message.answer(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.main_menu_keyboard()
        )
        await state.set_state(UserState.CHOOSING_CATEGORY)

        logger.info(f"✅ Пользователь {message.from_user.id} запустил бота")

    except Exception as e:
        logger.error(f"❌ Ошибка в cmd_start: {e}")
        await message.answer(
            "❌ Произошла ошибка. Пожалуйста, попробуйте позже.",
            reply_markup=keyboards.main_menu_keyboard()
        )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по боту"""
    help_text = (
        "📚 <b>Справка по боту</b>\n\n"
        "<b>Основные функции:</b>\n"
        "💇‍♀️ <b>Волосы</b> — персонализированный подбор косметики\n"
        "🧴 <b>Тело</b> — уход по потребностям кожи\n\n"
        "<b>Как работает подбор:</b>\n"
        "1. Выбираете категорию (волосы/тело)\n"
        "2. Отвечаете на вопросы о типе/проблемах\n"
        "3. Получаете рекомендации и фото продуктов\n\n"
        "<b>Админ-панель:</b>\n"
        "Для загрузки фото используйте команду /admin"
    )

    await message.answer(
        help_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.main_menu_keyboard()
    )

@dp.message(Command("status"))
async def cmd_status(message: Message):
    """Проверка статуса бота"""
    try:
        # Проверяем подключение к БД
        db_status = photo_db.is_connected
        photo_count = await photo_db.count_photos()

        # Получаем статистику по категориям
        hair_photos = await photo_db.get_photos_by_category("волосы")
        body_photos = await photo_db.get_photos_by_category("тело")

        status_text = (
            "📊 <b>Статус системы</b>\n\n"
            f"🤖 <b>Бот:</b> Активен ✅\n"
            f"🗄️ <b>База данных:</b> {'Подключена ✅' if db_status else 'Ошибка ❌'}\n\n"
            f"📈 <b>Статистика фото:</b>\n"
            f"• Всего: {photo_count}\n"
            f"• Волосы: {len(hair_photos)}\n"
            f"• Тело: {len(body_photos)}\n\n"
            f"🕐 <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}"
        )

        await message.answer(
            status_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.main_menu_keyboard()
        )

    except Exception as e:
        logger.error(f"❌ Ошибка в cmd_status: {e}")
        await message.answer("❌ Ошибка при получении статуса")

@dp.message(Command("dbcheck"))
async def cmd_dbcheck(message: Message):
    """Проверка состояния базы данных"""
    try:
        db_connected = photo_db.is_connected
        photo_count = await photo_db.count_photos()
        all_photos = await photo_db.get_all_photos()

        check_text = (
            "🔍 <b>Проверка базы данных</b>\n\n"
            f"• Подключена: {'✅' if db_connected else '❌'}\n"
            f"• Всего фото: {photo_count}\n\n"
            "<b>Последние записи:</b>\n"
        )

        if all_photos:
            for i, photo in enumerate(all_photos[:5], 1):
                check_text += f"{i}. {photo.get('product_key', 'N/A')} - {photo.get('display_name', 'N/A')}\n"
            if len(all_photos) > 5:
                check_text += f"... и еще {len(all_photos) - 5} записей\n"
        else:
            check_text += "• Таблица пуста\n"

        await message.answer(check_text, parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"❌ Ошибка проверки БД: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:100]}")

@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Доступ к админ-панели"""
    await state.set_state(AdminState.WAITING_PASSWORD)
    await message.answer(
        "🔐 <b>Доступ к админ-панели</b>\n\n"
        "Введите пароль для входа:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.back_to_menu_keyboard()
    )

# ==================== ГЛАВНОЕ МЕНЮ И ВЫБОР КАТЕГОРИИ ====================

@dp.message(F.text == "🏠 Главное меню")
async def process_main_menu(message: Message, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    clear_selected_problems(message.from_user.id)

    welcome_text = (
        "👋 <b>Добро пожаловать в SVOY AV.COSMETIC!</b>\n\n"
        "<i>Выберите категорию:</i>"
    )
    await message.answer(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.main_menu_keyboard()
    )
    await state.set_state(UserState.CHOOSING_CATEGORY)

@dp.message(F.text == "🔄 Новая подборка")
async def process_new_selection(message: Message, state: FSMContext):
    """Начать новую подборку"""
    await state.clear()
    clear_selected_problems(message.from_user.id)

    await message.answer(
        "🔄 <b>Начинаем новую подборку!</b>\n\n"
        "<i>Выберите категорию:</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.main_menu_keyboard()
    )
    await state.set_state(UserState.CHOOSING_CATEGORY)

@dp.message(UserState.CHOOSING_CATEGORY, F.text == "💇‍♀️ Волосы")
async def process_hair_category(message: Message, state: FSMContext):
    """Выбрана категория 'Волосы'"""
    clear_selected_problems(message.from_user.id)
    await state.set_state(UserState.HAIR_CHOOSING_TYPE)
    await message.answer(
        "💇‍♀️ <b>Отлично! Подберем уход для волос.</b>\n\n"
        "<i>Какой у вас тип волос?</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.hair_type_keyboard()
    )

@dp.message(UserState.CHOOSING_CATEGORY, F.text == "🧴 Тело")
async def process_body_category(message: Message, state: FSMContext):
    """Выбрана категория 'Тело'"""
    await state.set_state(UserState.BODY_CHOOSING_GOAL)
    await message.answer(
        "🧴 <b>Прекрасно! Займемся уходом за телом.</b>\n\n"
        "<i>Какова ваша основная цель ухода?</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.body_goals_keyboard()
    )

# ==================== ОПРОС ДЛЯ ТЕЛА ====================

@dp.message(UserState.BODY_CHOOSING_GOAL, F.text.in_(config.BODY_GOALS))
async def process_body_goal(message: Message, state: FSMContext):
    """Обработка цели ухода за телом"""
    try:
        goal = message.text
        save_user_data(message.from_user.id, "body_goal", goal)

        # Получаем рекомендации и фото
        recommendations, photo_keys = await get_body_recommendations_with_photos(goal)

        # Отправляем рекомендации
        await message.answer(
            recommendations,
            parse_mode=ParseMode.HTML,
            reply_markup=final_menu_keyboard()
        )

        # Отправляем фото продуктов
        if photo_keys:
            await send_recommended_photos(
                message.chat.id,
                photo_keys,
                "🛍️ <b>Рекомендуемые продукты:</b>"
            )
        else:
            await message.answer(
                "📷 Фото продуктов для этой категории пока не загружены.",
                reply_markup=final_menu_keyboard()
            )

        # Добавляем информацию о точках продаж
        await message.answer(
            config.SALES_POINTS + "\n\n" + config.DELIVERY_INFO,
            parse_mode=ParseMode.HTML,
            reply_markup=final_menu_keyboard()
        )

        # Очищаем состояние, но сохраняем возможность новой подборки
        await state.clear()

        logger.info(f"✅ Пользователь {message.from_user.id} получил рекомендации для тела: {goal}")

    except Exception as e:
        logger.error(f"❌ Ошибка в process_body_goal: {e}")
        await message.answer(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=final_menu_keyboard()
        )
        await state.clear()

# ==================== ОПРОС ДЛЯ ВОЛОС ====================

@dp.message(UserState.HAIR_CHOOSING_TYPE, F.text.in_(config.HAIR_TYPES))
async def process_hair_type(message: Message, state: FSMContext):
    """Обработка типа волос"""
    hair_type = message.text
    save_user_data(message.from_user.id, "hair_type", hair_type)

    await state.set_state(UserState.HAIR_CHOOSING_PROBLEMS)
    await message.answer(
        f"✅ <b>{hair_type}</b>\n\n"
        "<i>Теперь выберите проблемы волос (можно несколько):</i>\n"
        "<b>Нажмите на проблему, чтобы выбрать/отменить</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.hair_problems_keyboard([])
    )

@dp.message(UserState.HAIR_CHOOSING_PROBLEMS)
async def process_hair_problems(message: Message, state: FSMContext):
    """Обработка выбора проблем волос"""
    logger.info(f"Обработка проблем: '{message.text}'")

    if message.text == "✅ Готово":
        selected_problems = get_selected_problems(message.from_user.id)
        logger.info(f"Выбрано проблем: {selected_problems}")

        if not selected_problems:
            await message.answer(
                "❌ Пожалуйста, выберите хотя бы одну проблему.",
                reply_markup=keyboards.hair_problems_keyboard([])
            )
            return

        await state.set_state(UserState.HAIR_CHOOSING_SCALP)
        await message.answer(
            "<i>Чувствительная кожа головы?</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.scalp_type_keyboard()
        )

    elif message.text.startswith("☐ ") or message.text.startswith("✅ "):
        problem = message.text.replace("✅ ", "").replace("☐ ", "")

        # Проверяем, есть ли такая проблема в списке
        if problem not in config.HAIR_PROBLEMS:
            logger.warning(f"⚠️ Неизвестная проблема: {problem}")
            return

        # Переключаем выбор
        current_problems = get_selected_problems(message.from_user.id)

        if problem in current_problems:
            remove_selected_problem(message.from_user.id, problem)
            logger.info(f"Убрана проблема: {problem}")
        else:
            add_selected_problem(message.from_user.id, problem)
            logger.info(f"Добавлена проблема: {problem}")

        # Обновляем клавиатуру
        await message.answer(
            "<i>Выберите проблемы волос (можно несколько):</i>\n"
            "<b>Нажмите на проблему, чтобы выбрать/отменить</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.hair_problems_keyboard(get_selected_problems(message.from_user.id))
        )

    elif message.text == "🏠 Главное меню":
        clear_selected_problems(message.from_user.id)
        await state.clear()
        await process_main_menu(message, state)

@dp.message(UserState.HAIR_CHOOSING_SCALP, F.text.in_(config.SCALP_TYPES))
async def process_scalp_type(message: Message, state: FSMContext):
    """Обработка типа кожи головы"""
    scalp_type = message.text
    save_user_data(message.from_user.id, "scalp_type", scalp_type)

    await state.set_state(UserState.HAIR_CHOOSING_VOLUME)
    await message.answer(
        "<i>Хотите добавить объем волосам?</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.hair_volume_keyboard()
    )

@dp.message(UserState.HAIR_CHOOSING_VOLUME, F.text.in_(config.HAIR_VOLUME))
async def process_hair_volume(message: Message, state: FSMContext):
    """Обработка желания добавить объем"""
    hair_volume = message.text
    save_user_data(message.from_user.id, "hair_volume", hair_volume)

    # Проверяем тип волос для определения необходимости выбора цвета
    hair_type = get_user_data_value(message.from_user.id, "hair_type", "")

    if hair_type in ["Окрашенные блондинки", "Окрашенные все остальные"]:
        await state.set_state(UserState.HAIR_CHOOSING_COLOR)
        await message.answer(
            "<i>Выберите цвет волос:</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.hair_color_keyboard(hair_type)
        )
    else:
        # Для натуральных волос показываем результат сразу
        await show_hair_results(message, state)

@dp.message(UserState.HAIR_CHOOSING_COLOR, F.text.in_(["Блондинка", "Брюнетка", "Шатенка", "Русая", "Рыжая"]))
async def process_hair_color(message: Message, state: FSMContext):
    """Обработка цвета волос для окрашенных"""
    hair_color = message.text
    save_user_data(message.from_user.id, "hair_color", hair_color)

    await show_hair_results(message, state)

async def show_hair_results(message: Message, state: FSMContext):
    """Показать результаты для волос"""
    try:
        # Получаем все данные
        hair_type = get_user_data_value(message.from_user.id, "hair_type", "")
        problems = get_selected_problems(message.from_user.id)
        scalp_type = get_user_data_value(message.from_user.id, "scalp_type", "")
        hair_volume = get_user_data_value(message.from_user.id, "hair_volume", "")
        hair_color = get_user_data_value(message.from_user.id, "hair_color", "")

        logger.info(f"📊 Данные для рекомендаций: {hair_type}, {problems}, {scalp_type}, {hair_volume}, {hair_color}")

        # Получаем рекомендации и фото
        recommendations, photo_keys = await get_hair_recommendations_with_photos(
            hair_type, problems, scalp_type, hair_volume, hair_color
        )

        # Отправляем рекомендации
        await message.answer(
            recommendations,
            parse_mode=ParseMode.HTML,
            reply_markup=final_menu_keyboard()
        )

        # Отправляем фото продуктов
        if photo_keys:
            await send_recommended_photos(
                message.chat.id,
                photo_keys,
                "🛍️ <b>Рекомендуемые продукты:</b>"
            )
        else:
            await message.answer(
                "📷 Фото продуктов для этих рекомендаций пока не загружены.",
                reply_markup=final_menu_keyboard()
            )

        # Добавляем информацию о точках продаж
        await message.answer(
            config.SALES_POINTS + "\n\n" + config.DELIVERY_INFO,
            parse_mode=ParseMode.HTML,
            reply_markup=final_menu_keyboard()
        )

        # Очищаем состояние
        await state.clear()
        clear_selected_problems(message.from_user.id)

        logger.info(f"✅ Пользователь {message.from_user.id} получил рекомендации для волос")

    except Exception as e:
        logger.error(f"❌ Ошибка в show_hair_results: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при формировании рекомендаций. Попробуйте позже.",
            reply_markup=final_menu_keyboard()
        )
        await state.clear()

# ==================== АДМИН-ПАНЕЛЬ ====================

@dp.message(AdminState.WAITING_PASSWORD)
async def process_admin_password(message: Message, state: FSMContext):
    """Проверка пароля админа"""
    if message.text == config.ADMIN_PASSWORD:
        await state.set_state(AdminState.ADMIN_MAIN_MENU)
        await message.answer(
            "✅ <b>Доступ разрешен!</b>\n\n"
            "Добро пожаловать в админ-панель.",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.admin_category_keyboard()
        )
        logger.info(f"🔐 Пользователь {message.from_user.id} вошел в админ-панель")
    elif message.text == "🏠 Главное меню":
        await state.clear()
        await process_main_menu(message, state)
    else:
        await message.answer("❌ Неверный пароль. Попробуйте еще раз или нажмите 'Главное меню'.")

@dp.message(AdminState.ADMIN_MAIN_MENU, F.text == "📊 Статистика")
async def process_admin_stats(message: Message):
    """Показать статистику админки"""
    try:
        photo_count = await photo_db.count_photos()
        all_photos = await photo_db.get_all_photos()

        stats_text = "📊 <b>Статистика базы данных</b>\n\n"
        stats_text += f"📈 <b>Всего фото:</b> {photo_count}\n\n"

        # Статистика по категориям
        categories = {}
        for photo in all_photos:
            cat = photo['category']
            categories[cat] = categories.get(cat, 0) + 1

        for cat, count in categories.items():
            stats_text += f"• <b>{cat}:</b> {count}\n"

        await message.answer(
            stats_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.admin_category_keyboard()
        )

    except Exception as e:
        logger.error(f"❌ Ошибка в process_admin_stats: {e}")
        await message.answer("❌ Ошибка при получении статистики.")

@dp.message(AdminState.ADMIN_MAIN_MENU, F.text.in_(["💇‍♀️ Волосы", "🧴 Тело"]))
async def process_admin_category(message: Message, state: FSMContext):
    """Выбор категории для загрузки фото"""
    category = "волосы" if message.text == "💇‍♀️ Волосы" else "тело"

    await state.update_data(admin_category=category)
    await state.set_state(AdminState.ADMIN_CHOOSING_SUBCATEGORY)

    await message.answer(
        f"Выберите подкатегорию для <b>{category}</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.admin_subcategory_keyboard(category)
    )

@dp.message(AdminState.ADMIN_CHOOSING_SUBCATEGORY, F.text != "↩️ Назад к категориям")
async def process_admin_subcategory(message: Message, state: FSMContext):
    """Выбор подкатегории"""
    data = await state.get_data()
    category = data.get("admin_category")
    subcategory = message.text

    if subcategory not in config.PHOTO_STRUCTURE.get(category, {}):
        await message.answer("❌ Неверная подкатегория. Пожалуйста, выберите из списка.")
        return

    await state.update_data(admin_subcategory=subcategory)
    await state.set_state(AdminState.ADMIN_CHOOSING_PRODUCT_NAME)

    await message.answer(
        f"Выберите продукт в подкатегории <b>{subcategory}</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.admin_products_keyboard(category, subcategory)
    )

@dp.message(AdminState.ADMIN_CHOOSING_SUBCATEGORY, F.text == "↩️ Назад к категориям")
async def process_admin_back_to_categories(message: Message, state: FSMContext):
    """Возврат к выбору категории"""
    await state.set_state(AdminState.ADMIN_MAIN_MENU)
    await message.answer(
        "Выберите категорию:",
        reply_markup=keyboards.admin_category_keyboard()
    )

@dp.message(AdminState.ADMIN_CHOOSING_PRODUCT_NAME, F.text != "↩️ Назад к подкатегориям")
async def process_admin_product(message: Message, state: FSMContext):
    """Выбор продукта"""
    data = await state.get_data()
    category = data.get("admin_category")
    subcategory = data.get("admin_subcategory")
    product_display_name = message.text

    # Находим ключ продукта по display_name
    product_key = None
    for key, name in config.PHOTO_STRUCTURE[category][subcategory]:
        if name == product_display_name:
            product_key = key
            break

    if not product_key:
        await message.answer("❌ Продукт не найден. Пожалуйста, выберите из списка.")
        return

    await state.update_data(
        admin_product_key=product_key,
        admin_display_name=product_display_name
    )

    await state.set_state(AdminState.ADMIN_WAITING_PHOTO)
    await message.answer(
        f"📷 <b>Теперь отправьте фото для продукта:</b>\n\n"
        f"<b>Продукт:</b> {product_display_name}\n"
        f"<b>Категория:</b> {category}\n"
        f"<b>Подкатегория:</b> {subcategory}\n\n"
        f"<i>Отправьте одно фото.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )
    )

@dp.message(AdminState.ADMIN_CHOOSING_PRODUCT_NAME, F.text == "↩️ Назад к подкатегориям")
async def process_admin_back_to_subcategories(message: Message, state: FSMContext):
    """Возврат к выбору подкатегории"""
    data = await state.get_data()
    category = data.get("admin_category")

    await state.set_state(AdminState.ADMIN_CHOOSING_SUBCATEGORY)
    await message.answer(
        f"Выберите подкатегорию для <b>{category}</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.admin_subcategory_keyboard(category)
    )

@dp.message(AdminState.ADMIN_WAITING_PHOTO, F.photo)
async def process_admin_photo(message: Message, state: FSMContext):
    """Обработка фото для загрузки"""
    try:
        data = await state.get_data()
        product_key = data.get("admin_product_key")
        category = data.get("admin_category")
        subcategory = data.get("admin_subcategory")
        display_name = data.get("admin_display_name")

        # Проверяем, что все данные есть
        if not all([product_key, category, subcategory, display_name]):
            await message.answer("❌ Ошибка: данные продукта не найдены.")
            await state.set_state(AdminState.ADMIN_MAIN_MENU)
            await message.answer(
                "Возврат в админ-меню.",
                reply_markup=keyboards.admin_category_keyboard()
            )
            return

        # Получаем file_id
        photo = message.photo[-1]
        file_id = photo.file_id

        # Сохраняем в базу
        success = await photo_db.save_photo(
            product_key=product_key,
            category=category,
            subcategory=subcategory,
            display_name=display_name,
            file_id=file_id
        )

        if success:
            # Получаем текущее количество фото
            photo_count = await photo_db.count_photos()

            await message.answer(
                f"✅ <b>Фото успешно загружено!</b>\n\n"
                f"<b>Продукт:</b> {display_name}\n"
                f"<b>Категория:</b> {category}\n"
                f"<b>Подкатегория:</b> {subcategory}\n"
                f"<b>Ключ:</b> <code>{product_key}</code>\n\n"
                f"📊 <b>Всего фото в базе:</b> {photo_count}",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboards.admin_category_keyboard()
            )
            logger.info(f"✅ Админ загрузил фото: {product_key} ({display_name})")
        else:
            await message.answer(
                "❌ <b>Ошибка при сохранении в базу данных!</b>\n\n"
                "Проверьте:\n"
                "1. Подключение к PostgreSQL\n"
                "2. Правильность DATABASE_URL\n"
                "3. Доступность базы данных",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboards.admin_category_keyboard()
            )

        await state.set_state(AdminState.ADMIN_MAIN_MENU)

    except Exception as e:
        logger.error(f"❌ Ошибка при обработке фото админа: {e}", exc_info=True)
        await message.answer(
            f"❌ <b>Критическая ошибка:</b>\n\n<code>{str(e)[:200]}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.admin_category_keyboard()
        )
        await state.set_state(AdminState.ADMIN_MAIN_MENU)

@dp.message(AdminState.ADMIN_WAITING_PHOTO, F.text == "❌ Отмена")
async def process_admin_cancel_photo(message: Message, state: FSMContext):
    """Отмена загрузки фото"""
    await state.set_state(AdminState.ADMIN_MAIN_MENU)
    await message.answer(
        "Загрузка фото отменена.",
        reply_markup=keyboards.admin_category_keyboard()
    )

# ==================== SELF-PING SYSTEM ====================

async def self_ping():
    """Функция для self-ping приложения"""
    global APP_URL

    if not APP_URL:
        # Пытаемся получить URL из переменных окружения Render
        render_url = os.getenv("RENDER_EXTERNAL_URL")
        if render_url:
            APP_URL = f"{render_url}/health"
        else:
            logger.warning("⚠️ RENDER_EXTERNAL_URL не установлен, self-ping не работает")
            return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(APP_URL, timeout=10) as response:
                if response.status == 200:
                    logger.info(f"✅ Self-ping успешен: {APP_URL}")
                else:
                    logger.warning(f"⚠️ Self-ping вернул статус {response.status}: {APP_URL}")
    except Exception as e:
        logger.error(f"❌ Ошибка self-ping: {e}")

def run_scheduler():
    """Запуск планировщика для self-ping"""
    # Пингуем сразу при запуске
    asyncio.run(self_ping())

    # Запускаем пинг каждые 5 минут
    schedule.every(5).minutes.do(lambda: asyncio.run(self_ping()))

    while True:
        schedule.run_pending()
        time.sleep(1)

# ==================== ЗАПУСК БОТА ====================

async def on_startup():
    """Действия при запуске бота"""
    logger.info("🤖 Бот запускается...")

    # Инициализация базы данных
    db_connected = await photo_db.init_db()
    if not db_connected:
        logger.error("❌ Не удалось подключиться к базе данных!")
    else:
        photo_count = await photo_db.count_photos()
        logger.info(f"📊 Фото в базе: {photo_count}")

    # Запуск health check сервера
    if KEEP_ALIVE_AVAILABLE:
        keep_alive()
        logger.info("🌐 Health check сервер запущен")
    else:
        logger.warning("⚠️ Health check сервер не запущен")

    # Запуск self-ping в отдельном потоке
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("🔔 Self-ping система запущена")

    # Установка webhook или опроса
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Бот готов к работе!")

async def on_shutdown():
    """Действия при выключении бота"""
    logger.info("🛑 Бот выключается...")
    await photo_db.close()
    logger.info("🗄️ Соединение с БД закрыто")

async def main():
    """Основная функция запуска бота"""
    try:
        # Регистрация обработчиков startup/shutdown
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        logger.info("🚀 Запуск бота...")

        # Запуск поллинга с обработкой конфликтов
        await dp.start_polling(
            bot, 
            skip_updates=True, 
            allowed_updates=dp.resolve_used_update_types(),
            handle_signals=True
        )

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"⚠️ Необработанное исключение: {e}", exc_info=True)
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
    
    async def index_handler(request):
        return web.Response(text='Bot is running!')
    
    app = web.Application()
    app.router.add_get('/health', health_handler)
    app.router.add_get('/', index_handler)
    
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
            # Пробуем определить из логики Render
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
    
    # Ждем 15 секунд после старта
    await asyncio.sleep(15)
    
    # Первый пинг
    await self_ping()
    
    # Затем каждые 4 минуты
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

async def get_body_recommendations_with_photos(goal: str) -> tuple:
    """Получение рекомендаций для тела с фото"""
    try:
        if goal in config.BODY_DATA:
            data = config.BODY_DATA[goal]
            text = f"{data['title']}\n\n"
            for product in data['products']:
                text += f"• {product}\n"
            if 'note' in data:
                text += f"\n{data['note']}"
        else:
            text = config.get_body_recommendations_html(goal)

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
        text = config.get_hair_recommendations_html(hair_type, problems, scalp_type, hair_volume, hair_color)
        photo_keys = []

        if hair_type in config.PHOTO_MAPPING.get("волосы", {}):
            photo_keys.extend(config.PHOTO_MAPPING["волосы"][hair_type])

        for problem in problems:
            if problem in config.PHOTO_MAPPING.get("волосы", {}):
                photo_keys.extend(config.PHOTO_MAPPING["волосы"][problem])

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

        photo_keys = list(set(photo_keys))
        return text, photo_keys

    except Exception as e:
        logger.error(f"❌ Ошибка получения рекомендаций для волос: {e}")
        return "Рекомендации временно недоступны.", []

# ==================== МИДЛВЕЙР ДЛЯ ПРОВЕРКИ БД ====================

@dp.update.middleware()
async def check_db_middleware(handler, event, data):
    if not photo_db.is_connected:
        logger.warning("⚠️ БД не подключена, пытаемся переподключиться...")
        try:
            await photo_db.init()
        except Exception as e:
            logger.error(f"❌ Ошибка при переподключении БД: {e}")
    return await handler(event, data)

# ==================== КОМАНДЫ БОТА ====================

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
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
    try:
        db_status = photo_db.is_connected
        photo_count = 0
        hair_photos = []
        body_photos = []

        if db_status:
            photo_count = await photo_db.count_photos()
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
    try:
        db_connected = photo_db.is_connected
        photo_count = 0
        all_photos = []

        if db_connected:
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
    await state.set_state(AdminState.WAITING_PASSWORD)
    await message.answer(
        "🔐 <b>Доступ к админ-панели</b>\n\nВведите пароль для входа:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.back_to_menu_keyboard()
    )

# ==================== ГЛАВНОЕ МЕНЮ И ВЫБОР КАТЕГОРИИ ====================

@dp.message(F.text == "🏠 Главное меню")
async def process_main_menu(message: Message, state: FSMContext):
    await state.clear()
    clear_selected_problems(message.from_user.id)

    welcome_text = "👋 <b>Добро пожаловать в SVOY AV.COSMETIC!</b>\n\n<i>Выберите категорию:</i>"
    await message.answer(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.main_menu_keyboard()
    )
    await state.set_state(UserState.CHOOSING_CATEGORY)

@dp.message(F.text == "🔄 Новая подборка")
async def process_new_selection(message: Message, state: FSMContext):
    await state.clear()
    clear_selected_problems(message.from_user.id)

    await message.answer(
        "🔄 <b>Начинаем новую подборку!</b>\n\n<i>Выберите категорию:</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.main_menu_keyboard()
    )
    await state.set_state(UserState.CHOOSING_CATEGORY)

@dp.message(UserState.CHOOSING_CATEGORY, F.text == "💇‍♀️ Волосы")
async def process_hair_category(message: Message, state: FSMContext):
    clear_selected_problems(message.from_user.id)
    await state.set_state(UserState.HAIR_CHOOSING_TYPE)
    await message.answer(
        "💇‍♀️ <b>Отлично! Подберем уход для волос.</b>\n\n<i>Какой у вас тип волос?</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.hair_type_keyboard()
    )

@dp.message(UserState.CHOOSING_CATEGORY, F.text == "🧴 Тело")
async def process_body_category(message: Message, state: FSMContext):
    await state.set_state(UserState.BODY_CHOOSING_GOAL)
    await message.answer(
        "🧴 <b>Прекрасно! Займемся уходом за телом.</b>\n\n<i>Какова ваша основная цель ухода?</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.body_goals_keyboard()
    )

# ==================== ОПРОС ДЛЯ ТЕЛА ====================

@dp.message(UserState.BODY_CHOOSING_GOAL, F.text.in_(config.BODY_GOALS))
async def process_body_goal(message: Message, state: FSMContext):
    try:
        goal = message.text
        save_user_data(message.from_user.id, "body_goal", goal)

        recommendations, photo_keys = await get_body_recommendations_with_photos(goal)

        await message.answer(
            recommendations,
            parse_mode=ParseMode.HTML,
            reply_markup=final_menu_keyboard()
        )

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

        await message.answer(
            config.SALES_POINTS + "\n\n" + config.DELIVERY_INFO,
            parse_mode=ParseMode.HTML,
            reply_markup=final_menu_keyboard()
        )

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

        if problem not in config.HAIR_PROBLEMS:
            logger.warning(f"⚠️ Неизвестная проблема: {problem}")
            return

        current_problems = get_selected_problems(message.from_user.id)

        if problem in current_problems:
            remove_selected_problem(message.from_user.id, problem)
            logger.info(f"Убрана проблема: {problem}")
        else:
            add_selected_problem(message.from_user.id, problem)
            logger.info(f"Добавлена проблема: {problem}")

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
    hair_volume = message.text
    save_user_data(message.from_user.id, "hair_volume", hair_volume)

    hair_type = get_user_data_value(message.from_user.id, "hair_type", "")

    if hair_type in ["Окрашенные блондинки", "Окрашенные все остальные"]:
        await state.set_state(UserState.HAIR_CHOOSING_COLOR)
        await message.answer(
            "<i>Выберите цвет волос:</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.hair_color_keyboard(hair_type)
        )
    else:
        await show_hair_results(message, state)

@dp.message(UserState.HAIR_CHOOSING_COLOR, F.text.in_(["Блондинка", "Брюнетка", "Шатенка", "Русая", "Рыжая"]))
async def process_hair_color(message: Message, state: FSMContext):
    hair_color = message.text
    save_user_data(message.from_user.id, "hair_color", hair_color)
    await show_hair_results(message, state)

async def show_hair_results(message: Message, state: FSMContext):
    try:
        hair_type = get_user_data_value(message.from_user.id, "hair_type", "")
        problems = get_selected_problems(message.from_user.id)
        scalp_type = get_user_data_value(message.from_user.id, "scalp_type", "")
        hair_volume = get_user_data_value(message.from_user.id, "hair_volume", "")
        hair_color = get_user_data_value(message.from_user.id, "hair_color", "")

        logger.info(f"📊 Данные для рекомендаций: {hair_type}, {problems}, {scalp_type}, {hair_volume}, {hair_color}")

        recommendations, photo_keys = await get_hair_recommendations_with_photos(
            hair_type, problems, scalp_type, hair_volume, hair_color
        )

        await message.answer(
            recommendations,
            parse_mode=ParseMode.HTML,
            reply_markup=final_menu_keyboard()
        )

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

        await message.answer(
            config.SALES_POINTS + "\n\n" + config.DELIVERY_INFO,
            parse_mode=ParseMode.HTML,
            reply_markup=final_menu_keyboard()
        )

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
    if message.text == config.ADMIN_PASSWORD:
        await state.set_state(AdminState.ADMIN_MAIN_MENU)
        await message.answer(
            "✅ <b>Доступ разрешен!</b>\n\nДобро пожаловать в админ-панель.",
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
    try:
        photo_count = 0
        all_photos = []

        if photo_db.is_connected:
            photo_count = await photo_db.count_photos()
            all_photos = await photo_db.get_all_photos()

        stats_text = "📊 <b>Статистика базы данных</b>\n\n"
        stats_text += f"📈 <b>Всего фото:</b> {photo_count}\n\n"

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
    await state.set_state(AdminState.ADMIN_MAIN_MENU)
    await message.answer(
        "Выберите категорию:",
        reply_markup=keyboards.admin_category_keyboard()
    )

@dp.message(AdminState.ADMIN_CHOOSING_PRODUCT_NAME, F.text != "↩️ Назад к подкатегориям")
async def process_admin_product(message: Message, state: FSMContext):
    data = await state.get_data()
    category = data.get("admin_category")
    subcategory = data.get("admin_subcategory")
    product_display_name = message.text

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
    try:
        data = await state.get_data()
        product_key = data.get("admin_product_key")
        category = data.get("admin_category")
        subcategory = data.get("admin_subcategory")
        display_name = data.get("admin_display_name")

        if not all([product_key, category, subcategory, display_name]):
            await message.answer("❌ Ошибка: данные продукта не найдены.")
            await state.set_state(AdminState.ADMIN_MAIN_MENU)
            await message.answer(
                "Возврат в админ-меню.",
                reply_markup=keyboards.admin_category_keyboard()
            )
            return

        photo = message.photo[-1]
        file_id = photo.file_id

        success = await photo_db.save_photo(
            product_key=product_key,
            file_id=file_id,
            category=category,
            subcategory=subcategory,
            display_name=display_name
        )

        if success:
            photo_count = 0
            if photo_db.is_connected:
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
    await state.set_state(AdminState.ADMIN_MAIN_MENU)
    await message.answer(
        "Загрузка фото отменена.",
        reply_markup=keyboards.admin_category_keyboard()
    )

# ==================== ЗАПУСК БОТА ====================

async def on_startup():
    """Действия при запуске бота"""
    logger.info("🤖 Бот запускается...")

    # Инициализация базы данных
    try:
        await photo_db.init()
        logger.info(f"📊 Статус подключения к БД: {photo_db.is_connected}")
        
        if photo_db.is_connected:
            photo_count = await photo_db.count_photos()
            logger.info(f"📸 Фото в базе: {photo_count}")
        else:
            logger.warning("⚠️ База данных не подключена")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации БД: {e}")

    # ЗАПУСК HEALTH CHECK СЕРВЕРА
    try:
        health_runner = await start_health_server()
        logger.info("🌐 Health check сервер запущен")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска health check сервера: {e}")

    # ЗАПУСК SELF-PING СИСТЕМЫ
    asyncio.create_task(self_ping_task())
    logger.info("🔔 Self-ping система активирована")

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

        logger.info("🚀 Запуск бота с работающим health check...")

        # Запуск поллинга
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

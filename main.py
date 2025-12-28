"""
MAIN.PY - Основной файл бота для подбора косметики
"""

import os
import asyncio
import logging
import sys
import signal
from typing import List, Dict, Any
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery, 
    ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton,
    PhotoSize
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
import aiohttp
from aiohttp import ClientSession, ClientTimeout

# Импортируем наши модули
from photo_database import photo_db
from states import UserState, AdminState
from user_storage import (
    user_data_storage, save_user_data, get_user_data, 
    add_selected_problem, get_selected_problems, 
    clear_selected_problems
)
from keep_alive import start_health_server, stop_health_server

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin2026")
ADMINS = os.environ.get("ADMINS", "").split(",") if os.environ.get("ADMINS") else []

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не установлен!")
    exit(1)

# Инициализация бота
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Роутеры
user_router = Router()
admin_router = Router()
dp.include_router(user_router)
dp.include_router(admin_router)

# Глобальные переменные для self-ping
SELF_PING_TASK = None
SELF_PING_URL = None

# =============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ КЛАВИАТУР
# =============================================

def create_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню для пользователей"""
    keyboard = [
        [KeyboardButton(text="💇‍♀️ Для волос"), KeyboardButton(text="💅 Для тела")],
        [KeyboardButton(text="ℹ️ О боте"), KeyboardButton(text="👑 Админ-панель")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def create_hair_type_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора типа волос"""
    keyboard = [
        [KeyboardButton(text="👩‍🦰 Сухие"), KeyboardButton(text="👩‍🦱 Нормальные")],
        [KeyboardButton(text="👩‍🦳 Жирные"), KeyboardButton(text="👩‍🦲 Смешанные")],
        [KeyboardButton(text="↩️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def create_hair_problems_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора проблем волос"""
    keyboard = [
        [KeyboardButton(text="💔 Выпадение"), KeyboardButton(text="✨ Ломкость")],
        [KeyboardButton(text="🔥 Секущиеся кончики"), KeyboardButton(text="😴 Тусклость")],
        [KeyboardButton(text="🔍 Перхоть"), KeyboardButton(text="🎯 Зуд кожи головы")],
        [KeyboardButton(text="✅ Готово"), KeyboardButton(text="↩️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def create_scalp_type_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора типа кожи головы"""
    keyboard = [
        [KeyboardButton(text="🌵 Сухая"), KeyboardButton(text="🌊 Нормальная")],
        [KeyboardButton(text="💦 Жирная"), KeyboardButton(text="🎭 Чувствительная")],
        [KeyboardButton(text="↩️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def create_hair_volume_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора объема волос"""
    keyboard = [
        [KeyboardButton(text="💁‍♀️ Тонкие"), KeyboardButton(text="👩‍🦱 Средней толщины")],
        [KeyboardButton(text="👩‍🦰 Густые"), KeyboardButton(text="👑 Очень густые")],
        [KeyboardButton(text="↩️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def create_hair_color_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора цвета волос"""
    keyboard = [
        [KeyboardButton(text="👱‍♀️ Русые"), KeyboardButton(text="👩‍🦰 Рыжие")],
        [KeyboardButton(text="👩‍🦱 Брюнетка"), KeyboardButton(text="👩‍🦳 Блондинка")],
        [KeyboardButton(text="🎨 Окрашенные"), KeyboardButton(text="🌿 Натуральные")],
        [KeyboardButton(text="↩️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def create_body_goal_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора цели ухода за телом"""
    keyboard = [
        [KeyboardButton(text="💦 Увлажнение"), KeyboardButton(text="✨ Питание")],
        [KeyboardButton(text="🎯 Омоложение"), KeyboardButton(text="🍋 Детокс")],
        [KeyboardButton(text="🌿 Расслабление"), KeyboardButton(text="🏃‍♀️ Тонус")],
        [KeyboardButton(text="↩️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def create_admin_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню админ-панели"""
    keyboard = [
        [KeyboardButton(text="📤 Загрузить фото"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="👀 Просмотреть базу"), KeyboardButton(text="🗑️ Удалить фото")],
        [KeyboardButton(text="🔙 Выйти из админки")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def create_admin_categories_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура выбора категории для админа"""
    keyboard = [
        [KeyboardButton(text="💇‍♀️ Волосы"), KeyboardButton(text="💅 Тело")],
        [KeyboardButton(text="🔙 Назад в админ-меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def create_admin_subcategories_keyboard(category: str) -> ReplyKeyboardMarkup:
    """Клавиатура выбора подкатегории для админа"""
    subcategories = {
        "💇‍♀️ Волосы": ["🧴 Шампунь", "🌟 Кондиционер", "🎭 Маска", 
                      "💧 Сыворотка", "🌿 Масло", "✨ Спрей"],
        "💅 Тело": ["🚿 Гель для душа", "🧴 Крем для тела", "🧂 Скраб", 
                   "🌿 Масло для тела", "🛡️ Дезодорант", "👐 Крем для рук"]
    }
    
    keyboard = []
    for subcat in subcategories.get(category, []):
        keyboard.append([KeyboardButton(text=subcat)])
    keyboard.append([KeyboardButton(text="🔙 Назад")])
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# =============================================
# SELF-PING СИСТЕМА (для предотвращения сна)
# =============================================

async def start_self_ping():
    """Запуск self-ping системы для Render"""
    global SELF_PING_URL, SELF_PING_TASK
    
    # Получаем URL приложения из переменных окружения Render
    render_service_url = os.environ.get('RENDER_EXTERNAL_URL')
    
    if render_service_url:
        SELF_PING_URL = f"{render_service_url}/health"
        logger.info(f"🔔 Self-ping система активирована")
        logger.info(f"🌐 URL для self-ping: {SELF_PING_URL}")
        
        # Запускаем self-ping в фоне
        SELF_PING_TASK = asyncio.create_task(self_ping_worker())
        return True
    else:
        logger.info("ℹ️ Self-ping отключен (приложение не на Render)")
        return False

async def self_ping_worker():
    """Фоновый воркер для self-ping"""
    while True:
        try:
            # Ждем 5 минут между пингами
            await asyncio.sleep(300)  # 300 секунд = 5 минут
            
            # Отправляем ping
            await send_self_ping()
            
        except asyncio.CancelledError:
            logger.info("🛑 Self-ping worker остановлен")
            break
        except Exception as e:
            logger.error(f"❌ Ошибка в self-ping worker: {e}")
            # При ошибке ждем 1 минуту и пробуем снова
            await asyncio.sleep(60)

async def send_self_ping():
    """Отправка self-ping запроса"""
    global SELF_PING_URL
    
    if not SELF_PING_URL:
        return False
    
    try:
        timeout = ClientTimeout(total=30)
        async with ClientSession(timeout=timeout) as session:
            async with session.get(SELF_PING_URL) as response:
                if response.status == 200:
                    logger.info(f"✅ Self-ping успешен: {response.status}")
                    return True
                else:
                    logger.warning(f"⚠️ Self-ping вернул статус: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Ошибка при self-ping: {e}")
        return False

async def stop_self_ping():
    """Остановка self-ping системы"""
    global SELF_PING_TASK
    
    if SELF_PING_TASK:
        SELF_PING_TASK.cancel()
        try:
            await SELF_PING_TASK
        except asyncio.CancelledError:
            pass
        logger.info("🛑 Self-ping система остановлена")

# =============================================
# ПОЛЬЗОВАТЕЛЬСКИЕ ОБРАБОТЧИКИ
# =============================================

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    await state.set_state(UserState.MAIN_MENU)
    
    welcome_text = """
    👋 *Привет, красавица!* 

✨ Я — твой личный бот-консультант по косметике от салона *«Волосы&Beauty»*!

🌸 Я помогу тебе подобрать идеальные средства для:
    • 💇‍♀️ *Волос* — шампуни, маски, сыворотки
    • 💅 *Тела* — гели, кремы, скрабы

🎀 Просто выбери категорию, и я задам несколько вопросов, чтобы понять, что нужно именно твоим волосам или коже!

💖 *Давай начнем твою красивую историю?* 
    """
    
    await message.answer(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_main_keyboard()
    )

@user_router.message(UserState.MAIN_MENU, F.text == "💇‍♀️ Для волос")
async def choose_hair_category(message: Message, state: FSMContext):
    """Выбрана категория 'Для волос'"""
    await state.set_state(UserState.HAIR_CHOOSING_TYPE)
    await message.answer(
        "💇‍♀️ *Отлично! Давай узнаем больше о твоих волосах!*\n\n"
        "🎀 *Какой у тебя тип волос?*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_hair_type_keyboard()
    )

@user_router.message(UserState.MAIN_MENU, F.text == "💅 Для тела")
async def choose_body_category(message: Message, state: FSMContext):
    """Выбрана категория 'Для тела'"""
    await state.set_state(UserState.BODY_CHOOSING_GOAL)
    await message.answer(
        "💅 *Прекрасно! Позаботимся о твоей коже тела!*\n\n"
        "🌸 *Какую цель ухода ты преследуешь?*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_body_goal_keyboard()
    )

@user_router.message(UserState.MAIN_MENU, F.text == "ℹ️ О боте")
async def about_bot(message: Message):
    """Информация о боте"""
    about_text = """
    🌸 *О боте «Волосы&Beauty»*

✨ Я создан, чтобы помогать тебе выбирать идеальную косметику для волос и тела!

🎀 *Что я умею:*
    • 🔍 Анализировать твой тип волос и кожи
    • 💡 Давать персонализированные рекомендации
    • 📸 Показывать фото продуктов
    • 🛒 Помогать с выбором средств

💖 *Наша философия:*
    Мы верим, что каждая девушка заслуживает индивидуального подхода к красоте!

👑 *Для салонов:*
    Хочешь такой же бот для своего салона?
    Пиши: @svoy_cosmetics_support

🌸 *С любовью, команда «Волосы&Beauty»*
    """
    await message.answer(about_text, parse_mode=ParseMode.MARKDOWN)

@user_router.message(UserState.MAIN_MENU, F.text == "👑 Админ-панель")
async def admin_panel_request(message: Message, state: FSMContext):
    """Запрос доступа к админ-панели"""
    await state.set_state(AdminState.WAITING_PASSWORD)
    await message.answer(
        "🔐 *Введите пароль для доступа к админ-панели:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Отмена")]],
            resize_keyboard=True
        )
    )

@user_router.message(UserState.MAIN_MENU)
async def handle_main_menu(message: Message):
    """Обработчик главного меню"""
    await message.answer(
        "🌸 *Пожалуйста, выбери одну из кнопок меню:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_main_keyboard()
    )

# =============================================
# ОБРАБОТЧИКИ ДЛЯ ВОЛОС
# =============================================

@user_router.message(UserState.HAIR_CHOOSING_TYPE)
async def hair_type_handler(message: Message, state: FSMContext):
    """Обработчик выбора типа волос"""
    if message.text == "↩️ Назад":
        await state.set_state(UserState.MAIN_MENU)
        await message.answer(
            "🌸 *Возвращаемся в главное меню!*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_main_keyboard()
        )
        return
    
    hair_types = {
        "👩‍🦰 Сухие": "сухие",
        "👩‍🦱 Нормальные": "нормальные",
        "👩‍🦳 Жирные": "жирные",
        "👩‍🦲 Смешанные": "смешанные"
    }
    
    if message.text not in hair_types:
        await message.answer("🌸 *Пожалуйста, выбери тип волос из предложенных вариантов:*",
                           parse_mode=ParseMode.MARKDOWN)
        return
    
    hair_type = hair_types[message.text]
    save_user_data(message.from_user.id, "hair_type", hair_type)
    clear_selected_problems(message.from_user.id)
    
    await state.set_state(UserState.HAIR_CHOOSING_PROBLEMS)
    await message.answer(
        f"💖 *Отлично! Твой тип волос: {hair_type.capitalize()}*\n\n"
        "✨ *Есть ли у тебя проблемы с волосами?*\n"
        "🎀 *Можно выбрать несколько вариантов, а затем нажать «Готово»:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_hair_problems_keyboard()
    )

@user_router.message(UserState.HAIR_CHOOSING_PROBLEMS)
async def hair_problems_handler(message: Message, state: FSMContext):
    """Обработчик выбора проблем волос"""
    if message.text == "↩️ Назад":
        await state.set_state(UserState.HAIR_CHOOSING_TYPE)
        await message.answer(
            "💇‍♀️ *Выбери тип своих волос:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_hair_type_keyboard()
        )
        return
    
    problems_map = {
        "💔 Выпадение": "выпадение",
        "✨ Ломкость": "ломкость",
        "🔥 Секущиеся кончики": "секущиеся кончики",
        "😴 Тусклость": "тусклость",
        "🔍 Перхоть": "перхоть",
        "🎯 Зуд кожи головы": "зуд"
    }
    
    if message.text == "✅ Готово":
        selected_problems = get_selected_problems(message.from_user.id)
        if not selected_problems:
            selected_problems = ["нет проблем"]
        
        await state.set_state(UserState.HAIR_CHOOSING_SCALP)
        await message.answer(
            f"🌸 *Записала твои проблемы: {', '.join(selected_problems)}*\n\n"
            "🎀 *Теперь расскажи о типе кожи головы:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_scalp_type_keyboard()
        )
        return
    
    if message.text in problems_map:
        problem = problems_map[message.text]
        selected_problems = get_selected_problems(message.from_user.id)
        
        if problem in selected_problems:
            remove_selected_problem(message.from_user.id, problem)
            action = "убрала"
        else:
            add_selected_problem(message.from_user.id, problem)
            action = "добавила"
        
        selected_problems = get_selected_problems(message.from_user.id)
        count = len(selected_problems)
        
        await message.answer(
            f"✨ *Я {action} «{problem}»*\n"
            f"🎀 *Выбрано проблем: {count}*\n\n"
            "*Продолжай выбирать или нажми «Готово»:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_hair_problems_keyboard()
        )
    else:
        await message.answer("🌸 *Пожалуйста, выбери проблему из списка:*",
                           parse_mode=ParseMode.MARKDOWN)

@user_router.message(UserState.HAIR_CHOOSING_SCALP)
async def scalp_type_handler(message: Message, state: FSMContext):
    """Обработчик выбора типа кожи головы"""
    if message.text == "↩️ Назад":
        await state.set_state(UserState.HAIR_CHOOSING_PROBLEMS)
        await message.answer(
            "✨ *Выбери проблемы с волосами:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_hair_problems_keyboard()
        )
        return
    
    scalp_types = {
        "🌵 Сухая": "сухая",
        "🌊 Нормальная": "нормальная",
        "💦 Жирная": "жирная",
        "🎭 Чувствительная": "чувствительная"
    }
    
    if message.text not in scalp_types:
        await message.answer("🌸 *Пожалуйста, выбери тип кожи головы из предложенных:*",
                           parse_mode=ParseMode.MARKDOWN)
        return
    
    scalp_type = scalp_types[message.text]
    save_user_data(message.from_user.id, "scalp_type", scalp_type)
    
    await state.set_state(UserState.HAIR_CHOOSING_VOLUME)
    await message.answer(
        f"💖 *Записала: кожа головы — {scalp_type}*\n\n"
        "🌸 *Какой у тебя объем волос?*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_hair_volume_keyboard()
    )

@user_router.message(UserState.HAIR_CHOOSING_VOLUME)
async def hair_volume_handler(message: Message, state: FSMContext):
    """Обработчик выбора объема волос"""
    if message.text == "↩️ Назад":
        await state.set_state(UserState.HAIR_CHOOSING_SCALP)
        await message.answer(
            "🎀 *Выбери тип кожи головы:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_scalp_type_keyboard()
        )
        return
    
    volume_types = {
        "💁‍♀️ Тонкие": "тонкие",
        "👩‍🦱 Средней толщины": "средней толщины",
        "👩‍🦰 Густые": "густые",
        "👑 Очень густые": "очень густые"
    }
    
    if message.text not in volume_types:
        await message.answer("🌸 *Пожалуйста, выбери объем волос из предложенных:*",
                           parse_mode=ParseMode.MARKDOWN)
        return
    
    hair_volume = volume_types[message.text]
    save_user_data(message.from_user.id, "hair_volume", hair_volume)
    
    await state.set_state(UserState.HAIR_CHOOSING_COLOR)
    await message.answer(
        f"✨ *Отлично! Твои волосы — {hair_volume}*\n\n"
        "🎨 *Какой у тебя цвет волос?*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_hair_color_keyboard()
    )

@user_router.message(UserState.HAIR_CHOOSING_COLOR)
async def hair_color_handler(message: Message, state: FSMContext):
    """Обработчик выбора цвета волос"""
    if message.text == "↩️ Назад":
        await state.set_state(UserState.HAIR_CHOOSING_VOLUME)
        await message.answer(
            "🌸 *Выбери объем волос:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_hair_volume_keyboard()
        )
        return
    
    color_types = {
        "👱‍♀️ Русые": "русые",
        "👩‍🦰 Рыжие": "рыжие",
        "👩‍🦱 Брюнетка": "брюнет",
        "👩‍🦳 Блондинка": "блонд",
        "🎨 Окрашенные": "окрашенные",
        "🌿 Натуральные": "натуральные"
    }
    
    if message.text not in color_types:
        await message.answer("🌸 *Пожалуйста, выбери цвет волос из предложенных:*",
                           parse_mode=ParseMode.MARKDOWN)
        return
    
    hair_color = color_types[message.text]
    save_user_data(message.from_user.id, "hair_color", hair_color)
    
    # Генерируем результат
    await generate_hair_result(message, state)

async def generate_hair_result(message: Message, state: FSMContext):
    """Генерация результата для волос"""
    try:
        user_id = message.from_user.id
        user_data = get_user_data(user_id)
        
        hair_type = user_data.get("hair_type", "не указан")
        scalp_type = user_data.get("scalp_type", "не указан")
        hair_volume = user_data.get("hair_volume", "не указан")
        hair_color = user_data.get("hair_color", "не указан")
        problems = get_selected_problems(user_id)
        
        # Формируем рекомендации
        recommendations = []
        
        if hair_type == "сухие":
            recommendations.append("💧 *Увлажняющие маски* 2-3 раза в неделю")
            recommendations.append("🌿 *Масла для кончиков* ежедневно")
        elif hair_type == "жирные":
            recommendations.append("🍃 *Очищающие шампуни* для жирных волос")
            recommendations.append("✨ *Сухие шампуни* для экстренной помощи")
        else:
            recommendations.append("🌟 *Сбалансированный уход* для поддержания здоровья")
        
        if "выпадение" in problems:
            recommendations.append("💪 *Сыворотки для укрепления* с аминексилом")
        if "перхоть" in problems:
            recommendations.append("🎯 *Шампуни с цинком* или кетоконазолом")
        if "секущиеся кончики" in problems:
            recommendations.append("✂️ *Регулярная стрижка* кончиков раз в 2-3 месяца")
        
        if hair_color == "окрашенные":
            recommendations.append("🎨 *Специальные средства* для окрашенных волос")
            recommendations.append("🔒 *UV-защита* от выцветания")
        
        # Получаем продукты из базы данных
        products = await photo_db.get_recommended_products("💇‍♀️ Волосы")
        
        result_text = f"""
💖 *ТВОЙ ПЕРСОНАЛЬНЫЙ РЕЗУЛЬТАТ* 💖

👩 *Тип волос:* {hair_type.capitalize()}
🎯 *Проблемы:* {', '.join(problems) if problems else 'нет проблем'}
🌿 *Кожа головы:* {scalp_type.capitalize()}
💁 *Объем:* {hair_volume.capitalize()}
🎨 *Цвет:* {hair_color.capitalize()}

✨ *МОИ РЕКОМЕНДАЦИИ ДЛЯ ТЕБЯ:*
"""
        
        for i, rec in enumerate(recommendations, 1):
            result_text += f"\n    {i}. {rec}"
        
        result_text += "\n\n🌸 *Идеальные продукты для тебя:*"
        
        await state.set_state(UserState.SHOWING_RESULT)
        await message.answer(
            result_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Отправляем рекомендованные продукты
        if products:
            for product in products[:3]:  # Показываем первые 3 продукта
                try:
                    await message.answer_photo(
                        photo=product['file_id'],
                        caption=f"✨ *{product['display_name']}*\n\n"
                               f"🎀 Идеально подходит для твоего типа волос!\n"
                               f"💝 Рекомендуем к использованию!",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    await asyncio.sleep(0.5)  # Небольшая задержка между сообщениями
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки фото: {e}")
                    await message.answer(
                        f"✨ *{product['display_name']}*\n"
                        f"🌸 (Фото временно недоступно)",
                        parse_mode=ParseMode.MARKDOWN
                    )
        else:
            await message.answer(
                "🌸 *В базе пока нет продуктов для твоего типа волос.*\n"
                "🎀 *Администратор скоро добавит подходящие средства!*",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Предлагаем начать заново
        await message.answer(
            "💖 *Хочешь получить рекомендации для другой категории?*\n"
            "✨ *Или начать заново с волосами?*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка в generate_hair_result: {e}")
        await message.answer(
            "😔 *Упс! Произошла ошибка при генерации рекомендаций.*\n\n"
            "✨ *Попробуй начать заново командой /start*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_main_keyboard()
        )

# =============================================
# ОБРАБОТЧИКИ ДЛЯ ТЕЛА
# =============================================

@user_router.message(UserState.BODY_CHOOSING_GOAL)
async def body_goal_handler(message: Message, state: FSMContext):
    """Обработчик выбора цели ухода за телом"""
    if message.text == "↩️ Назад":
        await state.set_state(UserState.MAIN_MENU)
        await message.answer(
            "🌸 *Возвращаемся в главное меню!*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_main_keyboard()
        )
        return
    
    goals = {
        "💦 Увлажнение": "увлажнение",
        "✨ Питание": "питание",
        "🎯 Омоложение": "омоложение",
        "🍋 Детокс": "детокс",
        "🌿 Расслабление": "расслабление",
        "🏃‍♀️ Тонус": "тонус"
    }
    
    if message.text not in goals:
        await message.answer("🌸 *Пожалуйста, выбери цель из предложенных вариантов:*",
                           parse_mode=ParseMode.MARKDOWN)
        return
    
    body_goal = goals[message.text]
    save_user_data(message.from_user.id, "body_goal", body_goal)
    
    # Генерируем результат для тела
    await generate_body_result(message, state)

async def generate_body_result(message: Message, state: FSMContext):
    """Генерация результата для тела"""
    try:
        user_id = message.from_user.id
        body_goal = get_user_data(user_id).get("body_goal", "не указана")
        
        # Формируем рекомендации
        recommendations = []
        products_category = None
        
        if body_goal == "увлажнение":
            recommendations.append("💧 *Кремы с гиалуроновой кислотой*")
            recommendations.append("🌿 *Молочко для тела* после каждого душа")
            recommendations.append("🚿 *Увлажняющие гели для душа* без SLS")
            products_category = "💅 Тело"
            
        elif body_goal == "питание":
            recommendations.append("✨ *Богатые кремы* с маслами ши и какао")
            recommendations.append("🌰 *Питательные масла* для сухих участков")
            recommendations.append("🧴 *Бальзамы* для особенно сухой кожи")
            products_category = "💅 Тело"
            
        elif body_goal == "омоложение":
            recommendations.append("🎯 *Сыворотки с ретинолом* на ночь")
            recommendations.append("🌟 *Кремы с пептидами* для упругости")
            recommendations.append("✨ *Средства с витамином C* утром")
            products_category = "💅 Тело"
            
        elif body_goal == "детокс":
            recommendations.append("🍃 *Скрабы с морской солью* 2 раза в неделю")
            recommendations.append("🌿 *Гели для душа с углем* для глубокого очищения")
            recommendations.append("💦 *Тоники для тела* с кислотами")
            products_category = "💅 Тело"
            
        elif body_goal == "расслабление":
            recommendations.append("🛁 *Масла для ванны* с лавандой")
            recommendations.append("🌙 *Ночные кремы* с мелатонином")
            recommendations.append("✨ *Массажные масла* с ароматерапией")
            products_category = "💅 Тело"
            
        else:  # тонус
            recommendations.append("🏃‍♀️ *Охлаждающие гели* после тренировок")
            recommendations.append("💪 *Кремы с кофеином* против целлюлита")
            recommendations.append("✨ *Спреи для тела* с ментолом")
            products_category = "💅 Тело"
        
        result_text = f"""
💅 *ТВОЙ ПЕРСОНАЛЬНЫЙ РЕЗУЛЬТАТ ДЛЯ ТЕЛА* 💅

🎯 *Твоя цель:* {body_goal.capitalize()}

✨ *МОИ РЕКОМЕНДАЦИИ:*
"""
        
        for i, rec in enumerate(recommendations, 1):
            result_text += f"\n    {i}. {rec}"
        
        result_text += "\n\n🌸 *Идеальные продукты для тебя:*"
        
        await state.set_state(UserState.SHOWING_RESULT)
        await message.answer(
            result_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Отправляем рекомендованные продукты
        products = await photo_db.get_recommended_products(products_category)
        
        if products:
            for product in products[:3]:  # Показываем первые 3 продукта
                try:
                    await message.answer_photo(
                        photo=product['file_id'],
                        caption=f"✨ *{product['display_name']}*\n\n"
                               f"🎀 Идеально подходит для твоей цели!\n"
                               f"💝 Рекомендуем к использованию!",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки фото: {e}")
                    await message.answer(
                        f"✨ *{product['display_name']}*\n"
                        f"🌸 (Фото временно недоступно)",
                        parse_mode=ParseMode.MARKDOWN
                    )
        else:
            await message.answer(
                "🌸 *В базе пока нет продуктов для твоей цели.*\n"
                "🎀 *Администратор скоро добавит подходящие средства!*",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Предлагаем начать заново
        await message.answer(
            "💖 *Хочешь получить рекомендации для другой категории?*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка в generate_body_result: {e}")
        await message.answer(
            "😔 *Упс! Произошла ошибка при генерации рекомендаций.*\n\n"
            "✨ *Попробуй начать заново командой /start*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_main_keyboard()
        )

# =============================================
# АДМИНИСТРАТИВНЫЕ ОБРАБОТЧИКИ
# =============================================

@admin_router.message(AdminState.WAITING_PASSWORD)
async def admin_password_handler(message: Message, state: FSMContext):
    """Обработчик ввода пароля админа"""
    if message.text == "🔙 Отмена":
        await state.clear()
        await state.set_state(UserState.MAIN_MENU)
        await message.answer(
            "🌸 *Возвращаемся в главное меню!*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_main_keyboard()
        )
        return
    
    if message.text == ADMIN_PASSWORD:
        await state.set_state(AdminState.ADMIN_MAIN_MENU)
        count = await photo_db.count_photos()
        
        await message.answer(
            f"👑 *Добро пожаловать в админ-панель!*\n\n"
            f"📊 *Статистика базы:*\n"
            f"   • 📸 Фото в базе: {count}\n"
            f"   • 💾 База данных: {'✅ Подключена' if photo_db.is_connected else '❌ Отключена'}\n\n"
            f"✨ *Выбери действие:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_admin_main_keyboard()
        )
    else:
        await message.answer(
            "❌ *Неверный пароль!*\n"
            "🎀 *Попробуй еще раз или нажми «Отмена»:*",
            parse_mode=ParseMode.MARKDOWN
        )

@admin_router.message(AdminState.ADMIN_MAIN_MENU, F.text == "📤 Загрузить фото")
async def admin_upload_photo(message: Message, state: FSMContext):
    """Начало загрузки фото"""
    await state.set_state(AdminState.ADMIN_CHOOSING_CATEGORY)
    await message.answer(
        "📁 *Выбери категорию для загрузки фото:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_admin_categories_keyboard()
    )

@admin_router.message(AdminState.ADMIN_MAIN_MENU, F.text == "📊 Статистика")
async def admin_stats(message: Message):
    """Показать статистику"""
    count = await photo_db.count_photos()
    all_photos = await photo_db.get_all_photos()
    
    # Группируем по категориям
    categories = {}
    for photo in all_photos:
        cat = photo['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    stats_text = "📊 *СТАТИСТИКА БАЗЫ ДАННЫХ*\n\n"
    stats_text += f"📸 *Всего фото:* {count}\n\n"
    stats_text += "*По категориям:*\n"
    
    for cat, cat_count in categories.items():
        stats_text += f"   • {cat}: {cat_count} фото\n"
    
    if count == 0:
        stats_text += "\n🎀 *База пуста. Загрузи первые фото!*"
    
    await message.answer(
        stats_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_admin_main_keyboard()
    )

@admin_router.message(AdminState.ADMIN_MAIN_MENU, F.text == "👀 Просмотреть базу")
async def admin_view_database(message: Message):
    """Просмотр всей базы данных"""
    all_photos = await photo_db.get_all_photos()
    
    if not all_photos:
        await message.answer(
            "🎀 *База данных пуста!*\n"
            "✨ *Загрузи первое фото через меню «Загрузить фото»*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_admin_main_keyboard()
        )
        return
    
    # Группируем по категориям
    grouped = {}
    for photo in all_photos:
        cat = photo['category']
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(photo)
    
    for category, photos in grouped.items():
        category_text = f"📁 *{category}*\n\n"
        
        for photo in photos:
            category_text += f"✨ *{photo['display_name']}*\n"
            category_text += f"   🏷️ Ключ: `{photo['product_key']}`\n"
            category_text += f"   📂 Подкатегория: {photo['subcategory']}\n"
            
            # Форматируем дату
            if 'uploaded_at' in photo and photo['uploaded_at']:
                try:
                    if isinstance(photo['uploaded_at'], str):
                        upload_date = datetime.fromisoformat(photo['uploaded_at'].replace('Z', '+00:00'))
                    else:
                        upload_date = photo['uploaded_at']
                    
                    category_text += f"   📅 Загружено: {upload_date.strftime('%d.%m.%Y %H:%M')}\n"
                except:
                    category_text += f"   📅 Загружено: {photo['uploaded_at']}\n"
            
            category_text += "\n"
        
        # Разбиваем на части, если текст слишком длинный
        if len(category_text) > 4000:
            parts = [category_text[i:i+4000] for i in range(0, len(category_text), 4000)]
            for part in parts:
                await message.answer(part, parse_mode=ParseMode.MARKDOWN)
                await asyncio.sleep(0.3)
        else:
            await message.answer(category_text, parse_mode=ParseMode.MARKDOWN)
            await asyncio.sleep(0.3)
    
    await message.answer(
        "🌸 *Это все фото в базе данных!*\n"
        "✨ *Хочешь что-то изменить? Используй меню ниже:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_admin_main_keyboard()
    )

@admin_router.message(AdminState.ADMIN_MAIN_MENU, F.text == "🔙 Выйти из админки")
async def admin_exit(message: Message, state: FSMContext):
    """Выход из админ-панели"""
    await state.clear()
    await state.set_state(UserState.MAIN_MENU)
    await message.answer(
        "🌸 *Вы вышли из админ-панели!*\n"
        "✨ *Возвращаемся в главное меню:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_main_keyboard()
    )

# Остальные админ-обработчики (сокращенно, так как они длинные)
# Они остаются без изменений из предыдущего кода

# =============================================
# ОБЩИЕ ОБРАБОТЧИКИ
# =============================================

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
    🌸 *ПОМОЩЬ ПО КОМАНДАМ БОТА* ✨

    🎀 *Основные команды:*
    /start - Начать общение с ботом
    /help - Показать эту справку
    /admin - Войти в админ-панель (требуется пароль)

    💖 *Как пользоваться ботом:*
    1. Нажми /start или кнопку «Начать»
    2. Выбери категорию: Волосы или Тело
    3. Ответь на несколько вопросов о своих особенностях
    4. Получи персонализированные рекомендации с фото продуктов!

    👑 *Для администраторов:*
    - Войди в админ-панель через меню или команду /admin
    - Загружай фото продуктов в базу данных
    - Управляй содержимым базы

    ❓ *Проблемы или вопросы?*
    Напиши: @svoy_cosmetics_support

    💝 *Приятного пользования!*
    """
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Обработчик команды /admin"""
    await admin_panel_request(message, state)

@dp.message(Command("status"))
async def cmd_status(message: Message):
    """Показать статус бота"""
    count = await photo_db.count_photos()
    db_status = "✅ Подключена" if photo_db.is_connected else "❌ Отключена"
    
    status_text = f"""
    🤖 *Статус бота:*

    📊 *База данных:* {db_status}
    📸 *Фото в базе:* {count}
    🔔 *Self-ping:* {'✅ Активен' if SELF_PING_URL else '❌ Не активен'}
    
    🌸 *Бот работает нормально!*
    """
    await message.answer(status_text, parse_mode=ParseMode.MARKDOWN)

# =============================================
# ОСНОВНАЯ ФУНКЦИЯ ЗАПУСКА
# =============================================

async def shutdown_procedures(health_runner):
    """Процедуры завершения работы"""
    logger.info("🔧 Начинаем процедуры завершения...")
    
    # Останавливаем self-ping
    await stop_self_ping()
    
    # Останавливаем health server
    await stop_health_server(health_runner)
    
    # Закрываем соединение с базой данных
    await photo_db.close()
    
    logger.info("✅ Все процедуры завершения выполнены")

async def main():
    """Основная функция запуска бота"""
    logger.info("🚀 Запуск бота...")
    
    # Обработчик сигналов для корректного завершения
    loop = asyncio.get_running_loop()
    
    def signal_handler():
        logger.info("🛑 Получен сигнал завершения...")
        loop.create_task(shutdown())
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            logger.warning(f"⚠️ Сигнал {sig} не поддерживается на этой платформе")
    
    # Инициализируем базу данных
    logger.info("🔌 Подключаемся к базе данных...")
    db_success = await photo_db.init_db()
    
    if not db_success:
        logger.error("❌ Не удалось подключиться к базе данных!")
        logger.info("💡 Проверьте переменную окружения DATABASE_URL")
        return
    
    # Запускаем health server
    logger.info("🏥 Запускаем health server...")
    health_runner = await start_health_server()
    
    # Запускаем self-ping систему
    logger.info("🔔 Запускаем self-ping систему...")
    await start_self_ping()
    
    try:
        # Запускаем бота
        logger.info("🤖 Бот запущен и готов к работе!")
        logger.info("🌸 Используй /start для начала работы")
        logger.info("👑 Админ-панель: /admin (пароль: admin2026)")
        logger.info("📊 Статус: /status")
        
        await dp.start_polling(bot, skip_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске бота: {e}")
        
    finally:
        await shutdown_procedures(health_runner)

async def shutdown():
    """Корректное завершение работы"""
    logger.info("🛑 Завершение работы бота...")
    
    # Останавливаем polling
    await dp.stop_polling()
    
    # Даем время на завершение текущих операций
    await asyncio.sleep(1)
    
    logger.info("✅ Бот остановлен")
    sys.exit(0)

if __name__ == "__main__":
    # Проверяем наличие токена
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен! Укажите его в переменных окружения.")
        sys.exit(1)
    
    # Запускаем основную функцию
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Завершение по Ctrl+C")
    except Exception as e:
        logger.error(f"💥 Непредвиденная ошибка: {e}")

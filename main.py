import os
import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Optional
import schedule
import time
from threading import Thread

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

import photo_database
from states import UserState, AdminState
from user_storage import user_data_storage
from keep_alive import keep_alive

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получение переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin2026")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в переменных окружения")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Глобальная переменная для хранения URL приложения (для self-ping)
APP_URL = None

# ==================== КЛАВИАТУРЫ ====================

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💇‍♀️ Для волос"), KeyboardButton(text="💅 Для тела")],
            [KeyboardButton(text="ℹ️ О боте"), KeyboardButton(text="👑 Админ-панель")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите опцию..."
    )

def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой 'Назад'"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True
    )

def get_yes_no_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с Да/Нет"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

def get_hair_type_keyboard() -> ReplyKeyboardMarkup:
    """Выбор типа волос"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Сухие"), KeyboardButton(text="Нормальные")],
            [KeyboardButton(text="Жирные"), KeyboardButton(text="Смешанные")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

def get_hair_problems_keyboard() -> ReplyKeyboardMarkup:
    """Выбор проблем волос (можно выбрать несколько)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Выпадение"), KeyboardButton(text="Ломкость")],
            [KeyboardButton(text="Секущиеся кончики"), KeyboardButton(text="Тусклость")],
            [KeyboardButton(text="Перхоть"), KeyboardButton(text="Зуд")],
            [KeyboardButton(text="➡️ Далее"), KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

def get_scalp_type_keyboard() -> ReplyKeyboardMarkup:
    """Выбор типа кожи головы"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Сухая"), KeyboardButton(text="Нормальная")],
            [KeyboardButton(text="Жирная"), KeyboardButton(text="Чувствительная")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

def get_hair_volume_keyboard() -> ReplyKeyboardMarkup:
    """Выбор объема волос"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Тонкие"), KeyboardButton(text="Средней толщины")],
            [KeyboardButton(text="Густые"), KeyboardButton(text="Очень густые")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

def get_hair_color_keyboard() -> ReplyKeyboardMarkup:
    """Выбор цвета волос"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Русые"), KeyboardButton(text="Рыжие")],
            [KeyboardButton(text="Брюнетка"), KeyboardButton(text="Блондинка")],
            [KeyboardButton(text="Окрашенные"), KeyboardButton(text="Натуральные")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

def get_body_goal_keyboard() -> ReplyKeyboardMarkup:
    """Выбор цели ухода за телом"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Увлажнение"), KeyboardButton(text="Питание")],
            [KeyboardButton(text="Омоложение"), KeyboardButton(text="Детокс")],
            [KeyboardButton(text="Расслабление"), KeyboardButton(text="Тонус")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """Меню админ-панели"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📤 Загрузить фото"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="👀 Просмотреть базу"), KeyboardButton(text="🗑️ Удалить фото")],
            [KeyboardButton(text="⬅️ На главную")]
        ],
        resize_keyboard=True
    )

def get_categories_keyboard() -> ReplyKeyboardMarkup:
    """Выбор категории для загрузки фото"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Волосы"), KeyboardButton(text="Тело")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    try:
        await state.clear()
        await message.answer(
            "👋 Привет, красавица! Я твой личный помощник по подбору косметики.\n\n"
            "Я помогу подобрать идеальные средства для твоих волос и тела! 💖\n\n"
            "Выбери, что тебя интересует:",
            reply_markup=get_main_menu_keyboard()
        )
        logger.info(f"Пользователь {message.from_user.id} запустил бота")
        
        # Уведомление админа о новом пользователе
        if ADMIN_CHAT_ID:
            try:
                await bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"👤 Новый пользователь!\n"
                         f"ID: {message.from_user.id}\n"
                         f"Имя: {message.from_user.full_name}\n"
                         f"Юзернейм: @{message.from_user.username if message.from_user.username else 'нет'}"
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение админу: {e}")
    except Exception as e:
        logger.error(f"Ошибка в cmd_start: {e}")
        await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте позже.")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по боту"""
    help_text = (
        "📚 <b>Справка по боту</b>\n\n"
        "Я помогу подобрать косметику для волос и тела!\n\n"
        "💇‍♀️ <b>Для волос</b> - пройди небольшой опрос о типе волос и получи персонализированные рекомендации\n"
        "💅 <b>Для тела</b> - выбери цель ухода и получи подборку средств\n"
        "ℹ️ <b>О боте</b> - информация о возможностях бота\n"
        "👑 <b>Админ-панель</b> - для администраторов\n\n"
        "Используй кнопки меню для навигации!"
    )
    await message.answer(help_text, reply_markup=get_main_menu_keyboard())

@dp.message(Command("status"))
async def cmd_status(message: Message):
    """Проверка статуса бота и БД"""
    try:
        # Проверка подключения к БД
        db_status = await photo_database.check_connection()
        
        # Получение статистики
        stats = await photo_database.get_stats()
        
        status_text = (
            "📊 <b>Статус системы</b>\n\n"
            f"🤖 <b>Бот:</b> Активен ✅\n"
            f"🗄️ <b>База данных:</b> {'Подключена ✅' if db_status else 'Ошибка ❌'}\n\n"
            f"📈 <b>Статистика:</b>\n"
            f"• Всего фото: {stats.get('total', 0)}\n"
            f"• Волосы: {stats.get('hair', 0)}\n"
            f"• Тело: {stats.get('body', 0)}\n\n"
            f"👥 <b>Пользователи в памяти:</b> {len(user_data_storage)}\n"
            f"🕐 <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await message.answer(status_text)
    except Exception as e:
        logger.error(f"Ошибка в cmd_status: {e}")
        await message.answer("❌ Ошибка при получении статуса")

# ==================== ГЛАВНОЕ МЕНЮ ====================

@dp.message(F.text == "💇‍♀️ Для волос")
async def process_hair(message: Message, state: FSMContext):
    """Начало опроса для волос"""
    await state.set_state(UserState.WAITING_HAIR_TYPE)
    await message.answer(
        "💇‍♀️ <b>Отлично! Начнем подбор средств для волос.</b>\n\n"
        "Первый вопрос: какой у тебя тип волос?",
        reply_markup=get_hair_type_keyboard()
    )

@dp.message(F.text == "💅 Для тела")
async def process_body(message: Message, state: FSMContext):
    """Начало опроса для тела"""
    await state.set_state(UserState.WAITING_BODY_GOAL)
    await message.answer(
        "💅 <b>Прекрасно! Займемся уходом за телом.</b>\n\n"
        "Какова твоя основная цель ухода за телом?",
        reply_markup=get_body_goal_keyboard()
    )

@dp.message(F.text == "ℹ️ О боте")
async def process_about(message: Message):
    """Информация о боте"""
    about_text = (
        "🤖 <b>О боте «ВОЛОСЫ&BEAUTY»</b>\n\n"
        "Я — твой личный консультант по подбору косметики!\n\n"
        "✨ <b>Что я умею:</b>\n"
        "• Подбирать средства для волос по типу и проблемам\n"
        "• Рекомендовать уход за телом по целям\n"
        "• Показывать фотографии продуктов\n"
        "• Хранить базу косметических средств\n\n"
        "💡 <b>Как это работает:</b>\n"
        "1. Выбираешь категорию (волосы или тело)\n"
        "2. Отвечаешь на несколько вопросов\n"
        "3. Получаешь персонализированные рекомендации\n"
        "4. Смотришь фото продуктов из базы\n\n"
        "Начни с кнопки «Для волос» или «Для тела»! 🚀"
    )
    await message.answer(about_text, reply_markup=get_main_menu_keyboard())

@dp.message(F.text == "⬅️ Назад")
async def process_back(message: Message, state: FSMContext):
    """Обработка кнопки 'Назад'"""
    try:
        current_state = await state.get_state()
        
        # Определяем, на какой шаг вернуться
        if current_state == UserState.WAITING_HAIR_TYPE:
            await state.clear()
            await message.answer("Возвращаюсь в главное меню:", reply_markup=get_main_menu_keyboard())
        
        elif current_state == UserState.WAITING_HAIR_PROBLEMS:
            await state.set_state(UserState.WAITING_HAIR_TYPE)
            await message.answer("Выбери тип волос:", reply_markup=get_hair_type_keyboard())
        
        elif current_state == UserState.WAITING_SCALP_TYPE:
            await state.set_state(UserState.WAITING_HAIR_PROBLEMS)
            user_data = user_data_storage.get(message.from_user.id, {})
            problems = user_data.get('hair_problems', [])
            problems_text = ", ".join(problems) if problems else "не выбрано"
            await message.answer(
                f"Текущие проблемы: {problems_text}\n"
                "Можешь добавить ещё или нажать 'Далее':",
                reply_markup=get_hair_problems_keyboard()
            )
        
        elif current_state == UserState.WAITING_HAIR_VOLUME:
            await state.set_state(UserState.WAITING_SCALP_TYPE)
            await message.answer("Выбери тип кожи головы:", reply_markup=get_scalp_type_keyboard())
        
        elif current_state == UserState.WAITING_HAIR_COLOR:
            await state.set_state(UserState.WAITING_HAIR_VOLUME)
            await message.answer("Выбери объем волос:", reply_markup=get_hair_volume_keyboard())
        
        elif current_state == UserState.WAITING_BODY_GOAL:
            await state.clear()
            await message.answer("Возвращаюсь в главное меню:", reply_markup=get_main_menu_keyboard())
        
        elif current_state in AdminState:
            await state.clear()
            await message.answer("Возвращаюсь в главное меню:", reply_markup=get_main_menu_keyboard())
        
        else:
            await state.clear()
            await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
            
    except Exception as e:
        logger.error(f"Ошибка в process_back: {e}")
        await state.clear()
        await message.answer("Возвращаюсь в главное меню:", reply_markup=get_main_menu_keyboard())

@dp.message(F.text == "⬅️ На главную")
async def process_back_to_main(message: Message, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await message.answer("Возвращаюсь в главное меню:", reply_markup=get_main_menu_keyboard())

# ==================== ОПРОС ДЛЯ ВОЛОС ====================

@dp.message(UserState.WAITING_HAIR_TYPE, F.text.in_(["Сухие", "Нормальные", "Жирные", "Смешанные"]))
async def process_hair_type(message: Message, state: FSMContext):
    """Обработка типа волос"""
    user_data_storage.set(message.from_user.id, 'hair_type', message.text)
    await state.set_state(UserState.WAITING_HAIR_PROBLEMS)
    
    await message.answer(
        f"✅ Запомнила: {message.text.lower()} волосы.\n\n"
        "Теперь расскажи о проблемах волос (можно выбрать несколько):",
        reply_markup=get_hair_problems_keyboard()
    )

@dp.message(UserState.WAITING_HAIR_PROBLEMS)
async def process_hair_problems(message: Message, state: FSMContext):
    """Обработка проблем волос"""
    user_data = user_data_storage.get(message.from_user.id, {})
    problems = user_data.get('hair_problems', [])
    
    if message.text == "➡️ Далее":
        if problems:
            await state.set_state(UserState.WAITING_SCALP_TYPE)
            await message.answer(
                "Отлично! Теперь укажи тип кожи головы:",
                reply_markup=get_scalp_type_keyboard()
            )
        else:
            await message.answer("❌ Пожалуйста, выбери хотя бы одну проблему.")
    elif message.text in ["Выпадение", "Ломкость", "Секущиеся кончики", "Тусклость", "Перхоть", "Зуд"]:
        if message.text not in problems:
            problems.append(message.text)
            user_data_storage.set(message.from_user.id, 'hair_problems', problems)
        
        problems_text = ", ".join(problems)
        await message.answer(
            f"✅ Добавила: {message.text}\n\n"
            f"Текущие проблемы: {problems_text}\n"
            "Можешь добавить ещё или нажать 'Далее':",
            reply_markup=get_hair_problems_keyboard()
        )
    else:
        await message.answer("❌ Пожалуйста, используй кнопки ниже.")

@dp.message(UserState.WAITING_SCALP_TYPE, F.text.in_(["Сухая", "Нормальная", "Жирная", "Чувствительная"]))
async def process_scalp_type(message: Message, state: FSMContext):
    """Обработка типа кожи головы"""
    user_data_storage.set(message.from_user.id, 'scalp_type', message.text)
    await state.set_state(UserState.WAITING_HAIR_VOLUME)
    
    await message.answer(
        f"✅ Запомнила: {message.text.lower()} кожа головы.\n\n"
        "Какой у тебя объем волос?",
        reply_markup=get_hair_volume_keyboard()
    )

@dp.message(UserState.WAITING_HAIR_VOLUME, F.text.in_(["Тонкие", "Средней толщины", "Густые", "Очень густые"]))
async def process_hair_volume(message: Message, state: FSMContext):
    """Обработка объема волос"""
    user_data_storage.set(message.from_user.id, 'hair_volume', message.text)
    await state.set_state(UserState.WAITING_HAIR_COLOR)
    
    await message.answer(
        f"✅ Запомнила: {message.text.lower()} волосы.\n\n"
        "Последний вопрос: какой цвет волос?",
        reply_markup=get_hair_color_keyboard()
    )

@dp.message(UserState.WAITING_HAIR_COLOR, F.text.in_(["Русые", "Рыжие", "Брюнетка", "Блондинка", "Окрашенные", "Натуральные"]))
async def process_hair_color(message: Message, state: FSMContext):
    """Обработка цвета волос и вывод результата"""
    try:
        user_data_storage.set(message.from_user.id, 'hair_color', message.text)
        
        # Получаем все данные пользователя
        user_data = user_data_storage.get(message.from_user.id, {})
        
        # Формируем рекомендации
        recommendations = await generate_hair_recommendations(user_data)
        
        # Получаем фото продуктов из БД
        photos = await photo_database.get_photos_by_category("hair", limit=3)
        
        # Отправляем рекомендации
        await message.answer(
            recommendations,
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
        )
        
        # Отправляем фото, если есть
        if photos:
            await send_photos(message.chat.id, photos, "Вот подходящие средства для волос:")
        else:
            await message.answer("📷 Фото продуктов временно недоступны. База обновляется!")
        
        # Очищаем состояние
        await state.clear()
        
        logger.info(f"Пользователь {message.from_user.id} завершил опрос для волос")
        
    except Exception as e:
        logger.error(f"Ошибка в process_hair_color: {e}")
        await message.answer(
            "❌ Произошла ошибка при формировании рекомендаций. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()

async def generate_hair_recommendations(user_data: dict) -> str:
    """Генерация персонализированных рекомендаций для волос"""
    hair_type = user_data.get('hair_type', 'не указан')
    problems = user_data.get('hair_problems', [])
    scalp_type = user_data.get('scalp_type', 'не указан')
    volume = user_data.get('hair_volume', 'не указан')
    color = user_data.get('hair_color', 'не указан')
    
    # Базовые рекомендации
    rec_text = "💇‍♀️ <b>ПЕРСОНАЛИЗИРОВАННЫЕ РЕКОМЕНДАЦИИ</b>\n\n"
    
    # По типу волос
    type_rec = {
        "Сухие": "• Используйте увлажняющие шампуни и маски\n• Обязательно наносите масла на кончики\n• Избегайте частого мытья",
        "Нормальные": "• Поддерживающий уход с мягкими средствами\n• Периодические питательные маски\n• Защита от термического воздействия",
        "Жирные": "• Очищающие шампуни для жирных волос\n• Легкие кондиционеры только на кончики\n• Регулярное глубокое очищение",
        "Смешанные": "• Балансирующие средства\n• Разный уход для корней и кончиков\n• Маски для кончиков, легкие формулы для корней"
    }
    
    rec_text += f"<b>Для {hair_type.lower()} волос:</b>\n{type_rec.get(hair_type, '')}\n\n"
    
    # По проблемам
    if problems:
        rec_text += "<b>Для решения проблем:</b>\n"
        problem_solutions = {
            "Выпадение": "• Сыворотки для укрепления корней\n• Массаж кожи головы\n• Средства с кофеином и никотиновой кислотой",
            "Ломкость": "• Восстанавливающие маски\n• Белковые обработки\n• Защита от механических повреждений",
            "Секущиеся кончики": "• Регулярная стрижка\n• Масла и сыворотки для кончиков\n• Избегайте грубого расчесывания",
            "Тусклость": "• Осветляющие шампуни\n• Блеск-спреи\n• Полирующие сыворотки",
            "Перхоть": "• Противогрибковые шампуни\n• Успокаивающие средства для кожи головы\n• Регулярное отшелушивание",
            "Зуд": "• Успокаивающие средства с мятой\n• Гипоаллергенные формулы\n• Увлажнение кожи головы"
        }
        
        for problem in problems:
            if problem in problem_solutions:
                rec_text += f"• <b>{problem}:</b> {problem_solutions[problem]}\n"
        rec_text += "\n"
    
    # По типу кожи головы
    scalp_rec = {
        "Сухая": "• Используйте увлажняющие средства для кожи головы\n• Избегайте сушащих компонентов (SLS, спирт)\n• Масляные массажи",
        "Нормальная": "• Поддерживающий балансирующий уход\n• Регулярное мягкое очищение\n• Периодические пилинги",
        "Жирная": "• Регулирующие себум средства\n• Глубокое очищение\n• Матирующие сыворотки",
        "Чувствительная": "• Гипоаллергенные формулы\n• Успокаивающие ингредиенты (пантенол, аллантоин)\n• Избегайте агрессивных ПАВ"
    }
    
    rec_text += f"<b>Для {scalp_type.lower()} кожи головы:</b>\n{scalp_rec.get(scalp_type, '')}\n\n"
    
    # По объему
    volume_rec = {
        "Тонкие": "• Объемящие шампуни и спреи\n• Легкие текстуры, без утяжеления\n• Сухие шампуни для дополнительного объема",
        "Средней толщины": "• Укрепляющие и уплотняющие средства\n• Средней плотности текстуры\n• Термозащита при укладке",
        "Густые": "• Разглаживающие и увлажняющие средства\n• Более плотные текстуры\n• Средства для контроля объема",
        "Очень густые": "• Интенсивное увлажнение\n• Суперпитательные маски\n• Масла для контроля и блеска"
    }
    
    rec_text += f"<b>Для {volume.lower()} волос:</b>\n{volume_rec.get(volume, '')}\n\n"
    
    # По цвету
    color_rec = {
        "Русые": "• Средства для светлых волос\n• Оттеночные шампуни против желтизны\n• UV-защита от выгорания",
        "Рыжие": "• Усиливающие цвет средства\n• Защита от вымывания пигмента\n• Специальные линии для рыжих",
        "Брюнетка": "• Усиление глубины цвета\n• Средства с маслами для блеска\n• Защита от седины",
        "Блондинка": "• Осветляющий и ухаживающий уход\n• Фиолетовые шампуни\n• Интенсивное восстановление",
        "Окрашенные": "• Средства для окрашенных волос\n• Защита цвета от вымывания\n• Интенсивное восстановление структуры",
        "Натуральные": "• Поддерживающий натуральный уход\n• Усиление естественного блеска\n• Защита природного пигмента"
    }
    
    rec_text += f"<b>Для {color.lower()} волос:</b>\n{color_rec.get(color, '')}\n\n"
    
    rec_text += "✨ <b>Выбери средства из предложенных фото или обратись за консультацией!</b>"
    
    return rec_text

# ==================== ОПРОС ДЛЯ ТЕЛА ====================

@dp.message(UserState.WAITING_BODY_GOAL, F.text.in_(["Увлажнение", "Питание", "Омоложение", "Детокс", "Расслабление", "Тонус"]))
async def process_body_goal(message: Message, state: FSMContext):
    """Обработка цели ухода за телом"""
    try:
        goal = message.text
        user_data_storage.set(message.from_user.id, 'body_goal', goal)
        
        # Генерация рекомендаций
        recommendations = await generate_body_recommendations(goal)
        
        # Получаем фото продуктов из БД
        photos = await photo_database.get_photos_by_category("body", limit=3)
        
        # Отправляем рекомендации
        await message.answer(
            recommendations,
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
        )
        
        # Отправляем фото, если есть
        if photos:
            await send_photos(message.chat.id, photos, "Вот подходящие средства для тела:")
        else:
            await message.answer("📷 Фото продуктов временно недоступны. База обновляется!")
        
        # Очищаем состояние
        await state.clear()
        
        logger.info(f"Пользователь {message.from_user.id} завершил опрос для тела")
        
    except Exception as e:
        logger.error(f"Ошибка в process_body_goal: {e}")
        await message.answer(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()

async def generate_body_recommendations(goal: str) -> str:
    """Генерация рекомендаций для тела по цели"""
    goals = {
        "Увлажнение": {
            "title": "💦 ИНТЕНСИВНОЕ УВЛАЖНЕНИЕ",
            "recommendations": [
                "• Кремы и лосьоны с гиалуроновой кислотой",
                "• Масла для тела (миндальное, жожоба, аргановое)",
                "• Увлажняющие гели для душа без SLS",
                "• Сыворотки для сухой кожи",
                "• Питательные маски для тела"
            ],
            "ingredients": "гиалуроновая кислота, глицерин, мочевина, масло ши, сквалан"
        },
        "Питание": {
            "title": "🌿 ГЛУБОКОЕ ПИТАНИЕ",
            "recommendations": [
                "• Питательные кремы с маслами какао и ши",
                "• Восстанавливающие бальзамы",
                "• Масляные смеси для массажа",
                "• Скрабы с питательными маслами",
                "• Ночные маски для интенсивного восстановления"
            ],
            "ingredients": "масло ши, какао, ланолин, витамин Е, пчелиный воск"
        },
        "Омоложение": {
            "title": "✨ АНТИВОЗРАСТНОЙ УХОД",
            "recommendations": [
                "• Кремы с ретинолом и пептидами",
                "• Сыворотки с витамином С",
                "• Лифтинг-средства с коллагеном",
                "• Флюиды с SPF защитой",
                "• Маски для упругости кожи"
            ],
            "ingredients": "ретинол, витамин С, пептиды, коэнзим Q10, SPF"
        },
        "Детокс": {
            "title": "🌱 ДЕТОКС И ОЧИЩЕНИЕ",
            "recommendations": [
                "• Гели для душа с активированным углем",
                "• Скрабы с морской солью и водорослями",
                "• Обертывания с глиной",
                "• Тонизирующие спреи",
                "• Масла для лимфодренажного массажа"
            ],
            "ingredients": "активированный уголь, глина, морская соль, водоросли, мята"
        },
        "Расслабление": {
            "title": "🕯️ РЕЛАКС И СПОКОЙСТВИЕ",
            "recommendations": [
                "• Средства с лавандой и ромашкой",
                "• Масла для ванны",
                "• Кремы с ароматерапией",
                "• Соль для ванн с магнием",
                "• Успокаивающие бальзамы"
            ],
            "ingredients": "лаванда, ромашка, иланг-иланг, магний, мелисса"
        },
        "Тонус": {
            "title": "🏃‍♀️ ТОНУС И БОДРОСТЬ",
            "recommendations": [
                "• Охлаждающие гели",
                "• Кремы с кофеином",
                "• Антицеллюлитные средства",
                "• Скрабы с ментолом",
                "• Спреи для мгновенной свежести"
            ],
            "ingredients": "ментол, кофеин, экстракт конского каштана, гуарана, цитрусовые"
        }
    }
    
    goal_info = goals.get(goal, goals["Увлажнение"])
    
    text = f"💅 <b>{goal_info['title']}</b>\n\n"
    text += "<b>Рекомендуемые средства:</b>\n"
    for rec in goal_info["recommendations"]:
        text += f"{rec}\n"
    
    text += f"\n<b>Ключевые ингредиенты:</b>\n{goal_info['ingredients']}\n\n"
    text += "✨ <b>Выбери средства из предложенных фото для достижения цели!</b>"
    
    return text

# ==================== ОБРАБОТКА ФОТО ====================

async def send_photos(chat_id: int, photos: List[dict], caption: str = ""):
    """Отправка нескольких фото с подписями"""
    try:
        if not photos:
            return
        
        # Отправляем первое фото с общим заголовком
        first_photo = photos[0]
        await bot.send_photo(
            chat_id=chat_id,
            photo=first_photo['file_id'],
            caption=f"{caption}\n\n<b>{first_photo['display_name']}</b>\nКатегория: {first_photo['category']}\nТип: {first_photo['subcategory']}"
        )
        
        # Остальные фото отправляем по одному
        for photo in photos[1:]:
            await bot.send_photo(
                chat_id=chat_id,
                photo=photo['file_id'],
                caption=f"<b>{photo['display_name']}</b>\nКатегория: {photo['category']}\nТип: {photo['subcategory']}"
            )
            
    except Exception as e:
        logger.error(f"Ошибка при отправке фото: {e}")

# ==================== АДМИН-ПАНЕЛЬ ====================

@dp.message(F.text == "👑 Админ-панель")
async def process_admin_access(message: Message, state: FSMContext):
    """Доступ к админ-панели"""
    await state.set_state(AdminState.WAITING_PASSWORD)
    await message.answer(
        "🔐 <b>Доступ к админ-панели</b>\n\n"
        "Введите пароль для входа:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="⬅️ Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(AdminState.WAITING_PASSWORD)
async def process_admin_password(message: Message, state: FSMContext):
    """Проверка пароля админа"""
    if message.text == ADMIN_PASSWORD:
        await state.set_state(AdminState.MAIN_MENU)
        await message.answer(
            "✅ <b>Доступ разрешен!</b>\n\n"
            "Добро пожаловать в админ-панель. Выберите действие:",
            reply_markup=get_admin_menu_keyboard()
        )
        logger.info(f"Пользователь {message.from_user.id} вошел в админ-панель")
        
        # Уведомление админа о входе
        if ADMIN_CHAT_ID and str(message.from_user.id) != ADMIN_CHAT_ID:
            try:
                await bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"⚠️ Вход в админ-панель!\n"
                         f"ID: {message.from_user.id}\n"
                         f"Имя: {message.from_user.full_name}"
                )
            except:
                pass
    elif message.text == "⬅️ Назад":
        await state.clear()
        await message.answer("Возвращаюсь в главное меню:", reply_markup=get_main_menu_keyboard())
    else:
        await message.answer("❌ Неверный пароль. Попробуйте еще раз или нажмите 'Назад'.")

@dp.message(AdminState.MAIN_MENU, F.text == "📤 Загрузить фото")
async def process_upload_photo(message: Message, state: FSMContext):
    """Начало загрузки фото"""
    await state.set_state(AdminState.WAITING_CATEGORY)
    await message.answer(
        "📤 <b>Загрузка нового фото</b>\n\n"
        "Выберите категорию:",
        reply_markup=get_categories_keyboard()
    )

@dp.message(AdminState.WAITING_CATEGORY, F.text.in_(["Волосы", "Тело"]))
async def process_category(message: Message, state: FSMContext):
    """Обработка выбора категории"""
    await state.update_data(category=message.text)
    await state.set_state(AdminState.WAITING_SUBCATEGORY)
    
    if message.text == "Волосы":
        await message.answer(
            "Выберите подкатегорию (тип средства):\n\n"
            "• Шампунь\n• Кондиционер\n• Маска\n• Сыворотка\n• Масло\n• Спрей\n"
            "• Лосьон\n• Тоник\n• Пилинг\n• Другое",
            reply_markup=get_back_keyboard()
        )
    else:  # Тело
        await message.answer(
            "Выберите подкатегорию (тип средства):\n\n"
            "• Гель для душа\n• Скраб\n• Крем для тела\n• Масло для тела\n• Дезодорант\n"
            "• Антицеллюлитное средство\n• Крем для рук\n• Бальзам для губ\n• Другое",
            reply_markup=get_back_keyboard()
        )

@dp.message(AdminState.WAITING_SUBCATEGORY)
async def process_subcategory(message: Message, state: FSMContext):
    """Обработка подкатегории"""
    await state.update_data(subcategory=message.text)
    await state.set_state(AdminState.WAITING_PRODUCT_NAME)
    await message.answer(
        "Введите название продукта (для отображения пользователям):\n\n"
        "Пример: «Шампунь для объема L'Oreal Elseve»",
        reply_markup=get_back_keyboard()
    )

@dp.message(AdminState.WAITING_PRODUCT_NAME)
async def process_product_name(message: Message, state: FSMContext):
    """Обработка названия продукта"""
    await state.update_data(display_name=message.text)
    await state.set_state(AdminState.WAITING_PRODUCT_KEY)
    
    # Генерируем пример ключа
    data = await state.get_data()
    category = data.get('category', '').lower()
    subcategory = data.get('subcategory', '').lower().replace(' ', '_')
    name_part = message.text[:20].lower().replace(' ', '_')
    example_key = f"{category}_{subcategory}_{name_part}_1"
    
    await message.answer(
        f"Введите уникальный ключ продукта (латинскими буквами, без пробелов):\n\n"
        f"Пример: <code>{example_key}</code>\n\n"
        f"Этот ключ используется для идентификации в базе данных.",
        reply_markup=get_back_keyboard()
    )

@dp.message(AdminState.WAITING_PRODUCT_KEY)
async def process_product_key(message: Message, state: FSMContext):
    """Обработка ключа продукта"""
    product_key = message.text.strip()
    
    # Проверка формата ключа
    if ' ' in product_key or not product_key.replace('_', '').isalnum():
        await message.answer(
            "❌ Ключ должен содержать только латинские буквы, цифры и подчеркивания.\n"
            "Пожалуйста, введите ключ еще раз:",
            reply_markup=get_back_keyboard()
        )
        return
    
    # Проверка уникальности ключа
    exists = await photo_database.check_key_exists(product_key)
    if exists:
        await message.answer(
            "❌ Этот ключ уже существует в базе. Пожалуйста, введите другой ключ:",
            reply_markup=get_back_keyboard()
        )
        return
    
    await state.update_data(product_key=product_key)
    await state.set_state(AdminState.WAITING_PHOTO)
    await message.answer(
        "📷 Теперь отправьте фото продукта (одним изображением):",
        reply_markup=get_back_keyboard()
    )

@dp.message(AdminState.WAITING_PHOTO, F.photo)
async def process_product_photo(message: Message, state: FSMContext):
    """Обработка фото продукта"""
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        category = data.get('category')
        subcategory = data.get('subcategory')
        display_name = data.get('display_name')
        product_key = data.get('product_key')
        
        # Получаем file_id самого большого фото
        photo = message.photo[-1]
        file_id = photo.file_id
        
        # Сохраняем в базу данных
        success = await photo_database.save_photo(
            product_key=product_key,
            category=category,
            subcategory=subcategory,
            display_name=display_name,
            file_id=file_id
        )
        
        if success:
            await message.answer(
                f"✅ <b>Фото успешно загружено!</b>\n\n"
                f"<b>Ключ:</b> {product_key}\n"
                f"<b>Категория:</b> {category}\n"
                f"<b>Подкатегория:</b> {subcategory}\n"
                f"<b>Название:</b> {display_name}\n\n"
                "Что дальше?",
                reply_markup=get_admin_menu_keyboard()
            )
            await state.set_state(AdminState.MAIN_MENU)
            
            logger.info(f"Загружено новое фото: {product_key}")
        else:
            await message.answer(
                "❌ Ошибка при сохранении в базу данных. Попробуйте еще раз.",
                reply_markup=get_admin_menu_keyboard()
            )
            await state.set_state(AdminState.MAIN_MENU)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {e}")
        await message.answer(
            "❌ Ошибка при загрузке фото. Попробуйте еще раз.",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.set_state(AdminState.MAIN_MENU)

@dp.message(AdminState.MAIN_MENU, F.text == "📊 Статистика")
async def process_stats(message: Message):
    """Показ статистики базы данных"""
    try:
        stats = await photo_database.get_stats()
        
        stats_text = (
            "📊 <b>Статистика базы данных</b>\n\n"
            f"📈 <b>Всего фото:</b> {stats.get('total', 0)}\n\n"
            f"💇‍♀️ <b>Для волос:</b> {stats.get('hair', 0)}\n"
            f"💅 <b>Для тела:</b> {stats.get('body', 0)}\n\n"
            f"🕐 <b>Последнее обновление:</b> {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await message.answer(stats_text, reply_markup=get_admin_menu_keyboard())
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await message.answer("❌ Ошибка при получении статистики.")

@dp.message(AdminState.MAIN_MENU, F.text == "👀 Просмотреть базу")
async def process_view_database(message: Message):
    """Просмотр всей базы данных"""
    try:
        products = await photo_database.get_all_products()
        
        if not products:
            await message.answer("📭 База данных пуста.", reply_markup=get_admin_menu_keyboard())
            return
        
        # Разбиваем на группы по 10 для удобства чтения
        for i in range(0, len(products), 10):
            batch = products[i:i+10]
            batch_text = "📋 <b>База продуктов</b>\n\n"
            
            for idx, product in enumerate(batch, 1):
                batch_text += (
                    f"{i+idx}. <b>{product['display_name']}</b>\n"
                    f"   Ключ: <code>{product['product_key']}</code>\n"
                    f"   Категория: {product['category']}\n"
                    f"   Тип: {product['subcategory']}\n"
                    f"   Загружено: {product['uploaded_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
                )
            
            await message.answer(batch_text, reply_markup=get_admin_menu_keyboard())
            
    except Exception as e:
        logger.error(f"Ошибка при просмотре базы: {e}")
        await message.answer("❌ Ошибка при получении данных.")

@dp.message(AdminState.MAIN_MENU, F.text == "🗑️ Удалить фото")
async def process_delete_start(message: Message, state: FSMContext):
    """Начало процесса удаления фото"""
    try:
        # Получаем все продукты для отображения
        products = await photo_database.get_all_products()
        
        if not products:
            await message.answer("📭 Нет фото для удаления.", reply_markup=get_admin_menu_keyboard())
            return
        
        # Создаем инлайн-клавиатуру
        keyboard = []
        for product in products:
            button_text = f"{product['display_name']} ({product['category']})"
            callback_data = f"delete_{product['product_key']}"
            keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")])
        
        await message.answer(
            "🗑️ <b>Выберите фото для удаления:</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка при начале удаления: {e}")
        await message.answer("❌ Ошибка при получении списка фото.")

@dp.callback_query(F.data.startswith("delete_"))
async def process_delete_confirm(callback: CallbackQuery):
    """Подтверждение удаления фото"""
    product_key = callback.data.replace("delete_", "")
    
    # Получаем информацию о продукте
    product = await photo_database.get_product_by_key(product_key)
    
    if not product:
        await callback.answer("❌ Фото не найдено.")
        return
    
    # Показываем подтверждение
    confirm_text = (
        f"❓ <b>Подтвердите удаление</b>\n\n"
        f"<b>Название:</b> {product['display_name']}\n"
        f"<b>Ключ:</b> <code>{product['product_key']}</code>\n"
        f"<b>Категория:</b> {product['category']}\n"
        f"<b>Тип:</b> {product['subcategory']}\n\n"
        f"<i>Это действие нельзя отменить!</i>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{product_key}"),
            InlineKeyboardButton(text="❌ Нет, отмена", callback_data="cancel_delete")
        ]
    ])
    
    await callback.message.edit_text(confirm_text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("confirm_delete_"))
async def process_delete_execute(callback: CallbackQuery):
    """Выполнение удаления фото"""
    product_key = callback.data.replace("confirm_delete_", "")
    
    try:
        # Удаляем из базы данных
        success = await photo_database.delete_photo(product_key)
        
        if success:
            await callback.message.edit_text(
                f"✅ <b>Фото успешно удалено!</b>\n\n"
                f"Ключ: <code>{product_key}</code>",
                reply_markup=None
            )
            logger.info(f"Удалено фото: {product_key}")
        else:
            await callback.message.edit_text(
                "❌ Ошибка при удалении фото из базы данных.",
                reply_markup=None
            )
    except Exception as e:
        logger.error(f"Ошибка при удалении фото: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при удалении.",
            reply_markup=None
        )
    
    await callback.answer()

@dp.callback_query(F.data == "cancel_delete")
async def process_delete_cancel(callback: CallbackQuery):
    """Отмена удаления"""
    await callback.message.edit_text(
        "❌ Удаление отменено.",
        reply_markup=None
    )
    await callback.answer()

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
            logger.warning("RENDER_EXTERNAL_URL не установлен, self-ping не работает")
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
    await photo_database.init_db()
    logger.info("🗄️ База данных инициализирована")
    
    # Запуск health check сервера
    keep_alive()
    logger.info("🌐 Health check сервер запущен")
    
    # Запуск self-ping в отдельном потоке
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("🔔 Self-ping система запущена")
    
    # Установка webhook (если нужно) или опрос
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Бот готов к работе!")

async def on_shutdown():
    """Действия при выключении бота"""
    logger.info("🛑 Бот выключается...")
    await photo_database.close()
    logger.info("🗄️ Соединение с БД закрыто")

async def main():
    """Основная функция запуска бота"""
    try:
        # Регистрация обработчиков startup/shutdown
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        logger.info("🚀 Запуск бота...")
        
        # Запуск поллинга
        await dp.start_polling(bot, skip_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Необработанное исключение: {e}")

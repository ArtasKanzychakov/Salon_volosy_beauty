import asyncio
import logging
import os
import sys
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from config import BOT_TOKEN, WELCOME_TEXT, LOCATIONS_TEXT, DELIVERY_TEXT
from keyboards import get_main_menu, get_body_menu, get_hair_type_menu, get_final_menu
from database import delete_user_data, save_user_data, get_user_data
from recommendations import BODY_RECOMMENDATIONS, HAIR_RECOMMENDATIONS

# ========== НАСТРОЙКА ЛОГГИРОВАНИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Для отладки можно включить детальное логирование aiogram
# logging.getLogger('aiogram').setLevel(logging.DEBUG)

# ========== СОСТОЯНИЯ БОТА ==========
class UserState(StatesGroup):
    MAIN_MENU = State()        # Главное меню
    BODY_MENU = State()        # Меню ухода за телом
    HAIR_MENU = State()        # Меню выбора типа волос

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# ========== HTTP-СЕРВЕР ДЛЯ RENDER ==========
class HealthHandler(BaseHTTPRequestHandler):
    """Простой обработчик для проверки здоровья сервиса"""
    def do_GET(self):
        if self.path in ['/', '/health']:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Bot is alive')
            logger.info(f"HTTP: Health check from {self.client_address[0]}")
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Отключаем стандартное логирование запросов

def run_http_server():
    """Запускает HTTP-сервер в отдельном потоке"""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"🌐 HTTP-сервер запущен на порту {port}")
    print(f"✅ HTTP-сервер запущен на порту {port}")
    try:
        server.serve_forever()
    except Exception as e:
        logger.error(f"HTTP-сервер остановлен с ошибкой: {e}")

# ========== ОБРАБОТЧИКИ КОМАНД ==========
@router.message(CommandStart())
@router.message(Command("restart"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команд /start и /restart"""
    logger.info(f"Пользователь {message.from_user.id} вызвал /start")
    
    # Очищаем состояние и данные пользователя
    await state.clear()
    delete_user_data(message.from_user.id)
    
    # Устанавливаем состояние и показываем главное меню
    await state.set_state(UserState.MAIN_MENU)
    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu())
    logger.info(f"Состояние пользователя {message.from_user.id} установлено в MAIN_MENU")

@router.message(F.text == "◀️ Назад")
async def cmd_back(message: Message, state: FSMContext):
    """Обработчик кнопки 'Назад'"""
    logger.info(f"Пользователь {message.from_user.id} нажал 'Назад'")
    await cmd_start(message, state)

# ========== ГЛАВНОЕ МЕНЮ ==========
@router.message(F.text == "🧴 Уход за телом", UserState.MAIN_MENU)
async def body_menu_handler(message: Message, state: FSMContext):
    """Обработчик кнопки 'Уход за телом'"""
    logger.info(f"Пользователь {message.from_user.id} выбрал 'Уход за телом'")
    await state.set_state(UserState.BODY_MENU)
    await message.answer("Выберите тип ухода за телом:", reply_markup=get_body_menu())

@router.message(F.text == "💇‍♀️ Уход за волосами", UserState.MAIN_MENU)
async def hair_menu_handler(message: Message, state: FSMContext):
    """Обработчик кнопки 'Уход за волосами'"""
    logger.info(f"Пользователь {message.from_user.id} выбрал 'Уход за волосами'")
    await state.set_state(UserState.HAIR_MENU)
    await message.answer("Выберите тип ваших волос:", reply_markup=get_hair_type_menu())

# ========== УХОД ЗА ТЕЛОМ ==========
@router.message(UserState.BODY_MENU)
async def body_care_handler(message: Message, state: FSMContext):
    """Обработчик выбора ухода за телом"""
    user_choice = message.text
    logger.info(f"Пользователь {message.from_user.id} выбрал уход за телом: {user_choice}")
    
    if user_choice not in BODY_RECOMMENDATIONS:
        await message.answer("Пожалуйста, выберите вариант из меню ниже:", reply_markup=get_body_menu())
        return
    
    # Формируем ответ
    recommendation = BODY_RECOMMENDATIONS[user_choice]
    response_text = "\n".join(recommendation)
    response_text += f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"
    
    await message.answer(response_text, reply_markup=get_final_menu())
    await state.set_state(UserState.MAIN_MENU)

# ========== УХОД ЗА ВОЛОСАМИ ==========
@router.message(UserState.HAIR_MENU)
async def hair_care_handler(message: Message, state: FSMContext):
    """Обработчик выбора ухода за волосами"""
    user_choice = message.text
    logger.info(f"Пользователь {message.from_user.id} выбрал уход за волосами: {user_choice}")
    
    if user_choice not in HAIR_RECOMMENDATIONS:
        await message.answer("Пожалуйста, выберите вариант из меню ниже:", reply_markup=get_hair_type_menu())
        return
    
    # Формируем ответ
    recommendation = HAIR_RECOMMENDATIONS[user_choice]
    response_text = "\n".join(recommendation)
    response_text += f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"
    
    await message.answer(response_text, reply_markup=get_final_menu())
    await state.set_state(UserState.MAIN_MENU)

# ========== ФИНАЛЬНЫЕ ДЕЙСТВИЯ ==========
@router.message(F.text == "📍 Точки продаж")
async def locations_handler(message: Message):
    """Показать точки продаж"""
    logger.info(f"Пользователь {message.from_user.id} запросил точки продаж")
    await message.answer(LOCATIONS_TEXT, reply_markup=get_final_menu())

@router.message(F.text == "🚚 Заказать доставку")
async def delivery_handler(message: Message):
    """Показать информацию о доставке"""
    logger.info(f"Пользователь {message.from_user.id} запросил доставку")
    await message.answer(DELIVERY_TEXT, reply_markup=get_final_menu())

@router.message(F.text == "🔄 Новый подбор")
async def restart_handler(message: Message, state: FSMContext):
    """Новый подбор"""
    logger.info(f"Пользователь {message.from_user.id} начал новый подбор")
    await cmd_start(message, state)

# ========== ОБРАБОТЧИК НЕИЗВЕСТНЫХ СООБЩЕНИЙ ==========
@router.message()
async def unknown_handler(message: Message):
    """Обработчик неизвестных сообщений"""
    logger.warning(f"Неизвестное сообщение от {message.from_user.id}: {message.text}")
    await message.answer(
        "Я не понял ваше сообщение. Пожалуйста, используйте кнопки меню или команду /start",
        reply_markup=get_main_menu()
    )

# ========== ЗАПУСК БОТА ==========
async def run_bot():
    """Основная функция запуска бота"""
    logger.info("🚀 Запуск Telegram бота...")
    print("=" * 50)
    print("🤖 ТЕЛЕГРАМ-БОТ ДЛЯ КОСМЕТИКИ")
    print("=" * 50)
    
    # Запускаем поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

def main():
    """Точка входа в приложение"""
    # Запускаем HTTP-сервер в отдельном потоке (для Render)
    http_thread = Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Запускаем бота в основном потоке
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
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
from database import delete_user_data
from recommendations import BODY_RECOMMENDATIONS, HAIR_RECOMMENDATIONS

# ========== НАСТРОЙКА ЛОГГИРОВАНИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== СОСТОЯНИЯ БОТА ==========
class UserState(StatesGroup):
    MAIN_MENU = State()
    BODY_MENU = State()
    HAIR_MENU = State()

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# ========== HTTP-СЕРВЕР ДЛЯ RENDER ==========
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/', '/health']:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Bot is alive')
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, format, *args):
        pass

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"🌐 HTTP-сервер запущен на порту {port}")
    server.serve_forever()

# ========== ГЛАВНЫЙ ОБРАБОТЧИК (ЯДРО ИСПРАВЛЕНИЯ) ==========
@router.message()
async def universal_handler(message: Message, state: FSMContext):
    """УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК. Все сообщения идут сюда."""
    user_text = message.text
    current_state = await state.get_state()
    user_id = message.from_user.id

    logger.info(f"[ВХОД] User {user_id}, State: {current_state}, Text: '{user_text}'")

    # 1. Обработка команд /start, /restart и кнопки "Назад" в ЛЮБОМ состоянии
    if user_text in ["/start", "/restart", "◀️ Назад", "🔄 Новый подбор"]:
        logger.info(f"Сброс состояния для {user_id}")
        await state.clear()
        delete_user_data(user_id)
        await state.set_state(UserState.MAIN_MENU)
        await message.answer(WELCOME_TEXT, reply_markup=get_main_menu())
        return

    # 2. Определяем, что делать на основе ТЕКУЩЕГО состояния
    if current_state == UserState.MAIN_MENU:
        if user_text == "🧴 Уход за телом":
            logger.info(f"Пользователь {user_id} -> состояние BODY_MENU")
            await state.set_state(UserState.BODY_MENU)
            await message.answer("Выберите тип ухода за телом:", reply_markup=get_body_menu())
        elif user_text == "💇‍♀️ Уход за волосами":
            logger.info(f"Пользователь {user_id} -> состояние HAIR_MENU")
            await state.set_state(UserState.HAIR_MENU)
            await message.answer("Выберите тип ваших волос:", reply_markup=get_hair_type_menu())
        else:
            await message.answer("Пожалуйста, выберите категорию кнопкой ниже:", reply_markup=get_main_menu())

    elif current_state == UserState.BODY_MENU:
        # Пользователь в меню выбора ухода за телом
        if user_text in BODY_RECOMMENDATIONS:
            logger.info(f"Пользователь {user_id} выбрал уход за телом: {user_text}")
            recommendation = BODY_RECOMMENDATIONS[user_text]
            response = "\n".join(recommendation) + f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"
            await message.answer(response, reply_markup=get_final_menu())
            await state.set_state(UserState.MAIN_MENU)  # Возвращаем в главное меню
        else:
            # Если текст не распознан, показываем меню заново
            await message.answer("Пожалуйста, выберите вариант из меню ниже:", reply_markup=get_body_menu())

    elif current_state == UserState.HAIR_MENU:
        # Пользователь в меню выбора типа волос
        if user_text in HAIR_RECOMMENDATIONS:
            logger.info(f"Пользователь {user_id} выбрал тип волос: {user_text}")
            recommendation = HAIR_RECOMMENDATIONS[user_text]
            response = "\n".join(recommendation) + f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"
            await message.answer(response, reply_markup=get_final_menu())
            await state.set_state(UserState.MAIN_MENU)  # Возвращаем в главное меню
        else:
            # Если текст не распознан, показываем меню заново
            await message.answer("Пожалуйста, выберите вариант из меню ниже:", reply_markup=get_hair_type_menu())

    else:
        # Если состояние не определено (например, при первом запуске)
        logger.warning(f"Неизвестное состояние {current_state} для пользователя {user_id}. Сбрасываем.")
        await state.set_state(UserState.MAIN_MENU)
        await message.answer(WELCOME_TEXT, reply_markup=get_main_menu())

# ========== ФИНАЛЬНЫЕ ДЕЙСТВИЯ (работают из любого состояния) ==========
@router.message(F.text == "📍 Точки продаж")
async def locations_handler(message: Message):
    await message.answer(LOCATIONS_TEXT, reply_markup=get_final_menu())

@router.message(F.text == "🚚 Заказать доставку")
async def delivery_handler(message: Message):
    await message.answer(DELIVERY_TEXT, reply_markup=get_final_menu())

# ========== ЗАПУСК БОТА ==========
async def run_bot():
    logger.info("🚀 Запуск Telegram бота...")
    print("=" * 50)
    print("🤖 БОТ ЗАПУЩЕН (Упрощенная логика с одним обработчиком)")
    print("=" * 50)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

def main():
    http_thread = Thread(target=run_http_server, daemon=True)
    http_thread.start()
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
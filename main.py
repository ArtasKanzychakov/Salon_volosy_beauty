# main.py - ОБНОВЛЕННЫЙ с админ-панелью

import asyncio
import logging
import os
import sys
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from config import BOT_TOKEN, WELCOME_TEXT, LOCATIONS_TEXT, DELIVERY_TEXT
from keyboards import (
    get_main_menu, get_body_menu, get_hair_type_menu,
    get_hair_color_menu, get_hair_care_menu, get_hair_problems_menu,
    get_hair_additional_menu, get_final_menu
)
from body_data import BODY_DATA
from hair_data import HAIR_DATA
from database import (
    save_user_data, get_user_data, clear_user_data,
    add_selected_problem, get_selected_problems, clear_selected_problems
)
from multiselect import format_additional_problems
from admin_handlers import router as admin_router  # Импортируем админ-роутер
from photo_storage import photo_storage  # Импортируем хранилище фото

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
    HAIR_TYPE = State()
    HAIR_COLOR = State()
    HAIR_CARE = State()
    HAIR_PROBLEMS = State()
    HAIR_ADDITIONAL = State()

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)
dp.include_router(admin_router)  # Добавляем админ-роутер

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

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def format_body_response(data):
    response = f"{data['title']}\n\n"
    for product in data["products"]:
        response += f"• {product}\n"
    if "note" in data:
        response += f"\n<b>{data['note']}</b>\n"
    return response

def format_hair_response(data, selected_problems=None):
    response = f"{data['title']}\n\n"
    for product in data["products"]:
        response += f"• {product}\n"
    if "note" in data:
        response += f"\n<b>{data['note']}</b>\n"

    if selected_problems:
        response += format_additional_problems(selected_problems)

    return response

async def send_photo_if_exists(message: Message, photo_key: str, caption: str):
    """Отправить фото, если оно есть в хранилище"""
    photo_id = photo_storage.get_photo_id(photo_key)
    if photo_id:
        await message.answer_photo(photo_id, caption=caption, parse_mode="HTML")
        return True
    else:
        # Если фото нет, отправляем только текст
        await message.answer(caption, parse_mode="HTML")
        return False

# ========== ОБРАБОТЧИКИ КОМАНД ==========

# Старт
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    clear_user_data(message.from_user.id)
    clear_selected_problems(message.from_user.id)
    await state.clear()
    await state.set_state(UserState.MAIN_MENU)
    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu())

# Назад
@router.message(lambda message: message.text == "◀️ Назад")
async def back_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    user_id = message.from_user.id

    if current_state == UserState.BODY_MENU:
        await state.set_state(UserState.MAIN_MENU)
        await message.answer(WELCOME_TEXT, reply_markup=get_main_menu())

    elif current_state == UserState.HAIR_TYPE:
        await state.set_state(UserState.MAIN_MENU)
        await message.answer(WELCOME_TEXT, reply_markup=get_main_menu())

    elif current_state == UserState.HAIR_COLOR:
        await state.set_state(UserState.HAIR_TYPE)
        await message.answer("Выберите тип ваших волос:", reply_markup=get_hair_type_menu())

    elif current_state == UserState.HAIR_CARE:
        user_data = get_user_data(user_id)
        hair_type = user_data.get("hair_type")

        if hair_type == "colored":
            await state.set_state(UserState.HAIR_COLOR)
            await message.answer("Выберите цвет окрашенных волос:", reply_markup=get_hair_color_menu())
        else:
            await state.set_state(UserState.HAIR_TYPE)
            await message.answer("Выберите тип ваших волос:", reply_markup=get_hair_type_menu())

    elif current_state == UserState.HAIR_PROBLEMS:
        await state.set_state(UserState.HAIR_CARE)
        await message.answer("Выберите категорию ухода:", reply_markup=get_hair_care_menu())

    elif current_state == UserState.HAIR_ADDITIONAL:
        await state.set_state(UserState.HAIR_CARE)
        clear_selected_problems(user_id)
        await message.answer("Выберите категорию ухода:", reply_markup=get_hair_care_menu())

    else:
        await cmd_start(message, state)

# Главное меню
@router.message(lambda message: message.text == "🧴 Тело")
async def body_handler(message: Message, state: FSMContext):
    await state.set_state(UserState.BODY_MENU)
    await message.answer("Выберите тип ухода за телом:", reply_markup=get_body_menu())

@router.message(lambda message: message.text == "💇 Волосы")
async def hair_handler(message: Message, state: FSMContext):
    await state.set_state(UserState.HAIR_TYPE)
    await message.answer("Выберите тип ваших волос:", reply_markup=get_hair_type_menu())

# Финальные кнопки
@router.message(lambda message: message.text in ["📍 Точки", "🚚 Доставка", "🔄 Новый подбор"])
async def final_buttons_handler(message: Message, state: FSMContext):
    if message.text == "📍 Точки":
        await message.answer(LOCATIONS_TEXT, reply_markup=get_final_menu())
    elif message.text == "🚚 Доставка":
        await message.answer(DELIVERY_TEXT, reply_markup=get_final_menu())
    elif message.text == "🔄 Новый подбор":
        await cmd_start(message, state)

# ========== ОБРАБОТКА ТЕЛА С ФОТО ==========
@router.message(lambda message: message.text in BODY_DATA)
async def body_recommendation_handler(message: Message, state: FSMContext):
    choice = message.text
    data = BODY_DATA[choice]

    response = format_body_response(data)
    response += f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"

    # Определяем фото для категории тела
    photo_key = None
    if choice == "Общий уход":
        photo_key = "body_general"  # Нужно будет загрузить коллаж
    elif choice == "Сухая кожа":
        photo_key = "dry_skin"  # Нужно будет загрузить коллаж
    elif choice == "Чувствительная":
        photo_key = "sensitive_skin"  # Нужно будет загрузить коллаж
    elif choice == "Целлюлит":
        photo_key = "cellulite"  # Нужно будет загрузить коллаж
    
    # Пытаемся отправить фото
    if photo_key:
        sent = await send_photo_if_exists(message, photo_key, response)
        if not sent:
            await message.answer(response, reply_markup=get_final_menu())
    else:
        await message.answer(response, reply_markup=get_final_menu())
    
    await state.set_state(UserState.MAIN_MENU)

# ========== ОБРАБОТКА ВОЛОС С ФОТО ==========

# Выбор типа волос
@router.message(lambda message: message.text in [
    "👱‍♀️ Блондинки (окрашенные)",
    "🎨 Окрашенные волосы",
    "🌿 Натуральные волосы"
])
async def hair_type_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text == "👱‍♀️ Блондинки (окрашенные)":
        save_user_data(user_id, "hair_type", "blonde")
        save_user_data(user_id, "hair_color", None)
        await state.set_state(UserState.HAIR_CARE)
        await message.answer("Выберите категорию ухода:", reply_markup=get_hair_care_menu())

    elif message.text == "🎨 Окрашенные волосы":
        save_user_data(user_id, "hair_type", "colored")
        await state.set_state(UserState.HAIR_COLOR)
        await message.answer("Выберите цвет окрашенных волос:", reply_markup=get_hair_color_menu())

    elif message.text == "🌿 Натуральные волосы":
        save_user_data(user_id, "hair_type", "natural")
        save_user_data(user_id, "hair_color", None)
        await state.set_state(UserState.HAIR_CARE)
        await message.answer("Выберите категорию ухода:", reply_markup=get_hair_care_menu())

# Выбор цвета для окрашенных
@router.message(lambda message: message.text in ["Шатенка/Русая", "Рыжая"])
async def hair_color_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text == "Шатенка/Русая":
        save_user_data(user_id, "hair_color", "шатенка/русая")
    elif message.text == "Рыжая":
        save_user_data(user_id, "hair_color", "рыжая")

    await state.set_state(UserState.HAIR_CARE)
    await message.answer("Выберите категорию ухода:", reply_markup=get_hair_care_menu())

# Выбор категории ухода для волос С ФОТО
@router.message(lambda message: message.text in [
    "🧴 Общий уход",
    "⚡ Специфические проблемы",
    "❤️ Чувствительная кожа головы",
    "💨 Объем"
])
async def hair_category_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    hair_type = get_user_data(user_id, "hair_type")
    hair_color = get_user_data(user_id, "hair_color")

    if message.text == "🧴 Общий уход":
        if hair_type == "colored":
            if hair_color == "шатенка/русая":
                data = HAIR_DATA[hair_type]["colors"]["шатенка/русая"]["general"]
                photo_key = "colored_general_chocolate"
            elif hair_color == "рыжая":
                data = HAIR_DATA[hair_type]["colors"]["рыжая"]["general"]
                photo_key = "colored_general_copper"
            else:
                await message.answer("Пожалуйста, сначала выберите цвет волос.")
                return
        else:
            data = HAIR_DATA[hair_type]["general"]
            photo_key = f"{hair_type}_general"

        response = format_hair_response(data)
        response += f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"

        # Отправляем с фото
        sent = await send_photo_if_exists(message, photo_key, response)
        if not sent:
            await message.answer(response, reply_markup=get_final_menu())
        
        await state.set_state(UserState.MAIN_MENU)

    elif message.text == "⚡ Специфические проблемы":
        await state.set_state(UserState.HAIR_PROBLEMS)
        await message.answer("Выберите конкретную проблему:", reply_markup=get_hair_problems_menu())

    elif message.text == "❤️ Чувствительная кожа головы":
        data = HAIR_DATA[hair_type]["scalp"]
        response = format_hair_response(data)
        response += f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"

        # Пытаемся отправить фото для чувствительной кожи
        sent = await send_photo_if_exists(message, "sensitive_scalp", response)
        if not sent:
            await message.answer(response, reply_markup=get_final_menu())
        
        await state.set_state(UserState.MAIN_MENU)

    elif message.text == "💨 Объем":
        data = HAIR_DATA[hair_type]["volume"]
        response = format_hair_response(data)
        response += f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"

        # Отправляем с фото для объема
        sent = await send_photo_if_exists(message, "volume_care", response)
        if not sent:
            await message.answer(response, reply_markup=get_final_menu())
        
        await state.set_state(UserState.MAIN_MENU)

# Выбор "Общий уход + особенности"
@router.message(lambda message: message.text == "🧴 Общий уход + особенности")
async def hair_general_with_problems_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    hair_type = get_user_data(user_id, "hair_type")
    hair_color = get_user_data(user_id, "hair_color")

    clear_selected_problems(user_id)

    if hair_type == "colored":
        if not hair_color:
            await message.answer("Пожалуйста, сначала выберите цвет волос.")
            return

    await state.set_state(UserState.HAIR_ADDITIONAL)
    await message.answer(
        "Выберите дополнительные особенности ваших волос:\n"
        "(можно выбрать несколько, затем нажмите '✅ Готово')",
        reply_markup=get_hair_additional_menu()
    )

# Обработка выбора дополнительных проблем
@router.message(lambda message: message.text in [
    "Сухость", "Тонкие волосы", "Пушистость", "Тусклость"
])
async def additional_problem_handler(message: Message):
    user_id = message.from_user.id
    problem = message.text
    selected_problems = get_selected_problems(user_id)

    if problem in selected_problems:
        selected_problems.remove(problem)
        await message.answer(f"❌ Убрано: {problem}")
    else:
        add_selected_problem(user_id, problem)
        await message.answer(f"✅ Добавлено: {problem}")

    current_selected = get_selected_problems(user_id)
    if current_selected:
        await message.answer(
            f"<b>Вы выбрали:</b>\n• " + "\n• ".join(current_selected),
            reply_markup=get_hair_additional_menu()
        )

# Завершение выбора дополнительных проблем
@router.message(lambda message: message.text == "✅ Готово")
async def finish_additional_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    hair_type = get_user_data(user_id, "hair_type")
    hair_color = get_user_data(user_id, "hair_color")
    selected_problems = get_selected_problems(user_id)

    if hair_type == "colored":
        if hair_color == "шатенка/русая":
            data = HAIR_DATA[hair_type]["colors"]["шатенка/русая"]["general"]
            photo_key = "colored_general_chocolate"
        elif hair_color == "рыжая":
            data = HAIR_DATA[hair_type]["colors"]["рыжая"]["general"]
            photo_key = "colored_general_copper"
    else:
        data = HAIR_DATA[hair_type]["general"]
        photo_key = f"{hair_type}_general"

    response = format_hair_response(data, selected_problems)
    response += f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"

    # Отправляем с фото
    sent = await send_photo_if_exists(message, photo_key, response)
    if not sent:
        await message.answer(response, reply_markup=get_final_menu())
    
    await state.set_state(UserState.MAIN_MENU)
    clear_selected_problems(user_id)

# Выбор конкретной проблемы С ФОТО
@router.message(lambda message: message.text in [
    "Ломкость", "Выпадение", "Перхоть/зуд", "Секущиеся кончики",
    "Тусклость", "Пушистость", "Тонкие", "Очень поврежденные"
])
async def hair_problem_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    hair_type = get_user_data(user_id, "hair_type")
    problem = message.text

    if hair_type and problem in HAIR_DATA[hair_type]["problems"]:
        data = HAIR_DATA[hair_type]["problems"][problem]
        response = format_hair_response(data)
        response += f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"

        # Определяем ключ фото для проблемы
        photo_key = None
        if problem == "Ломкость":
            photo_key = f"{hair_type}_lomkost"
        elif problem == "Тусклость":
            photo_key = "hair_milk_concentrate"
        elif problem == "Пушистость":
            photo_key = "fluid_protein_elixir"
        elif problem == "Тонкие":
            photo_key = "thin_hair_care"
        elif problem == "Очень поврежденные":
            photo_key = "damaged_hair"
        elif problem == "Секущиеся кончики":
            photo_key = "oil_elixir"
        elif problem == "Выпадение":
            photo_key = "hair_loss"  # Нужно будет загрузить
        elif problem == "Перхоть/зуд":
            photo_key = "dandruff"  # Нужно будет загрузить

        # Отправляем с фото
        if photo_key:
            sent = await send_photo_if_exists(message, photo_key, response)
            if not sent:
                await message.answer(response, reply_markup=get_final_menu())
        else:
            await message.answer(response, reply_markup=get_final_menu())
        
        await state.set_state(UserState.MAIN_MENU)

# ========== ЗАПУСК БОТА ==========
async def run_bot():
    logger.info("🚀 Запуск Telegram бота с админ-панелью...")
    await bot.delete_webhook(drop_pending_updates=True)

    print("=" * 50)
    print("🤖 БОТ ЗАПУЩЕН")
    print("🔐 Админ-панель доступна по команде: admin2026")
    print("=" * 50)

    await dp.start_polling(bot)

def main():
    http_thread = Thread(target=run_http_server, daemon=True)
    http_thread.start()

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
import asyncio
import logging
import os
import sys
import signal
import hashlib
import socket
import json
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from config import BOT_TOKEN, WELCOME_TEXT, LOCATIONS_TEXT, DELIVERY_TEXT, FINAL_MESSAGE
from keyboards import *
from body_data import BODY_DATA
from hair_data import HAIR_DATA
from user_storage import *
# Импортируем ВСЁ из нового photo_database.py
from photo_database import photo_storage, PHOTO_KEYS
from states import UserState, AdminState
# Импортируем систему keep-alive
from keep_alive import start_keep_alive, stop_keep_alive, get_keep_alive_status

# ========== НАСТРОЙКА ЛОГГИРОВАНИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== ГЕНЕРАЦИЯ УНИКАЛЬНОГО ID ДЛЯ ЭКЗЕМПЛЯРА ==========
def get_instance_id():
    """Генерируем уникальный ID для этого экземпляра бота"""
    hostname = socket.gethostname()
    pid = os.getpid()
    unique_str = f"{hostname}_{pid}_{BOT_TOKEN[:10] if BOT_TOKEN else 'no_token'}"
    return hashlib.md5(unique_str.encode()).hexdigest()[:8]

INSTANCE_ID = get_instance_id()

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# ========== HTTP-СЕРВЕР ДЛЯ RENDER ==========
# Глобальная переменная для времени старта
START_TIME = None

class HealthHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP запросов для health checks"""
    
    def do_GET(self):
        """Обработка GET запросов"""
        if self.path in ['/', '/health', '/ping']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Основная информация о сервисе БЕЗ psutil
            response = {
                "status": "healthy",
                "service": "telegram-bot",
                "instance_id": INSTANCE_ID,
                "timestamp": time.time(),
                "uptime": time.time() - START_TIME if START_TIME else 0,
                "keep_alive_status": get_keep_alive_status()
            }
            
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "bot": "running",
                "instance": INSTANCE_ID,
                "web_server": "active",
                "keep_alive": "active"
            }
            
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Отключаем стандартное логирование HTTP запросов"""
        # Можно раскомментировать для отладки
        # logger.debug(f"HTTP: {args}")
        pass

def run_http_server():
    """Запуск HTTP сервера в отдельном потоке"""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"🌐 HTTP-сервер запущен на порту {port}")
    server.serve_forever()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
async def send_photo_if_exists(message: Message, photo_key: str, caption: str):
    """Отправить фото, если оно есть в хранилище"""
    try:
        if photo_key:
            photo_id = photo_storage.get_photo_id(photo_key)
            if photo_id:
                # Добавляем таймаут 10 секунд
                await asyncio.wait_for(
                    message.answer_photo(photo_id, caption=caption, parse_mode="HTML"),
                    timeout=10.0
                )
                return True
    except asyncio.TimeoutError:
        await message.answer("⏰ Фото загружается...")
        logger.warning(f"Таймаут при отправке фото: {photo_key}")
    except Exception as e:
        logger.error(f"Ошибка отправки фото {photo_key}: {e}")
    
    await message.answer(caption, parse_mode="HTML")
    return False

def format_body_recommendation(choice):
    """Форматировать рекомендацию для тела"""
    data = BODY_DATA[choice]

    response = f"{data['title']}\n\n"
    for product in data["products"]:
        response += f"• {product}\n"
    response += f"\n<b>{data['note']}</b>\n"

    return response

def format_hair_recommendation(user_id):
    """Форматировать полную рекомендацию для волос"""
    user_data = get_user_data(user_id)
    hair_type = user_data.get("hair_type")
    problems = get_selected_problems(user_id)
    sensitive_scalp = user_data.get("sensitive_scalp", False)
    need_volume = user_data.get("need_volume", False)
    hair_color = user_data.get("hair_color")

    response = "✨ <b>Отлично! Ваш персонализированный набор:</b>\n\n"

    if hair_type in ["blonde", "colored", "natural"]:
        base_care = HAIR_DATA["base_care"][hair_type]
        response += f"{base_care['title']}\n"
        for product in base_care["products"]:
            response += f"• {product}\n"
        response += "\n"

    if problems and "Общий уход" not in problems:
        for problem in problems:
            if problem in HAIR_DATA["problems"]:
                problem_data = HAIR_DATA["problems"][problem]
                response += f"{problem_data['title']}\n"
                for product in problem_data["products"]:
                    response += f"• {product}\n"
                response += "\n"

    if sensitive_scalp:
        scalp_data = HAIR_DATA["scalp"]
        response += f"{scalp_data['title']}\n"
        for product in scalp_data["products"]:
            response += f"• {product}\n"
        response += "\n"

    if need_volume:
        volume_data = HAIR_DATA["volume"]
        response += f"{volume_data['title']}\n"
        for product in volume_data["products"]:
            response += f"• {product}\n"
        response += "\n"

    if hair_type == "colored" and hair_color and hair_color in HAIR_DATA["color_masks"]:
        color_mask = HAIR_DATA["color_masks"][hair_color]
        response += f"🎨 <b>Для вашего цвета волос ({hair_color.lower()}):</b>\n"
        response += f"• {color_mask}\n\n"

    return response.strip()

# ========== ОБРАБОТЧИКИ КОМАНД ==========

# Старт и новый подбор
@router.message(CommandStart())
@router.message(F.text == "🔄 Новый подбор")
async def cmd_start(message: Message, state: FSMContext):
    """Начало нового подбора"""
    user_id = message.from_user.id
    delete_user_data(user_id)
    await state.set_state(UserState.MAIN_MENU)
    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu())

# Назад
@router.message(F.text == "◀️ Назад")
async def back_handler(message: Message, state: FSMContext):
    """Обработка кнопки Назад"""
    current_state = await state.get_state()
    user_id = message.from_user.id

    if current_state == UserState.BODY_CHOICE:
        await state.set_state(UserState.MAIN_MENU)
        await message.answer(WELCOME_TEXT, reply_markup=get_main_menu())

    elif current_state == UserState.HAIR_TYPE:
        await state.set_state(UserState.MAIN_MENU)
        await message.answer(WELCOME_TEXT, reply_markup=get_main_menu())

    elif current_state == UserState.HAIR_PROBLEMS:
        await state.set_state(UserState.HAIR_TYPE)
        await message.answer("❓ <b>Ваши волосы окрашены?</b>", reply_markup=get_hair_type_menu())

    elif current_state == UserState.HAIR_SCALP:
        await state.set_state(UserState.HAIR_PROBLEMS)
        problems = get_selected_problems(user_id)
        await message.answer(
            "❓ <b>С какими проблемами волос вы сталкиваетесь?</b>\n(можно выбрать несколько)",
            reply_markup=get_hair_problems_menu(problems)
        )

    elif current_state == UserState.HAIR_VOLUME:
        await state.set_state(UserState.HAIR_SCALP)
        await message.answer("❓ <b>Есть ли у вас чувствительная кожа головы?</b>", reply_markup=get_yes_no_menu())

    elif current_state == UserState.HAIR_COLOR:
        await state.set_state(UserState.HAIR_VOLUME)
        await message.answer("❓ <b>Вам нужен дополнительный акцент на объем?</b>", reply_markup=get_yes_no_menu())

    else:
        await cmd_start(message, state)

# ========== ГЛАВНОЕ МЕНЮ ==========
@router.message(F.text == "🧴 Тело")
async def body_handler(message: Message, state: FSMContext):
    """Выбрана категория Тело"""
    current_state = await state.get_state()

    # Разрешаем доступ из любых состояний, кроме админских
    if current_state not in [AdminState.MAIN, AdminState.UPLOAD, AdminState.WAITING_PHOTO,
                            AdminState.DELETE_SELECT, AdminState.DELETE_CONFIRM]:
        await state.set_state(UserState.BODY_CHOICE)
        await message.answer(
            "❓ <b>Какую главную задачу для кожи тела вы решаете?</b>",
            reply_markup=get_body_menu()
        )

@router.message(F.text == "💇 Волосы")
async def hair_handler(message: Message, state: FSMContext):
    """Выбрана категория Волосы"""
    current_state = await state.get_state()

    # Разрешаем доступ из любых состояний, кроме админских
    if current_state not in [AdminState.MAIN, AdminState.UPLOAD, AdminState.WAITING_PHOTO,
                            AdminState.DELETE_SELECT, AdminState.DELETE_CONFIRM]:
        await state.set_state(UserState.HAIR_TYPE)
        await message.answer(
            "❓ <b>Ваши волосы окрашены?</b>",
            reply_markup=get_hair_type_menu()
        )

# Финальные кнопки (работают из любого состояния)
@router.message(F.text.in_(["📍 Точки", "🚚 Доставка"]))
async def final_buttons_handler(message: Message):
    if message.text == "📍 Точки":
        await message.answer(LOCATIONS_TEXT, reply_markup=get_final_menu())
    elif message.text == "🚚 Доставка":
        await message.answer(DELIVERY_TEXT, reply_markup=get_final_menu())

# ========== ВЕТКА "ТЕЛО" ==========
@router.message(UserState.BODY_CHOICE, F.text.in_(BODY_DATA.keys()))
async def body_choice_handler(message: Message, state: FSMContext):
    """Пользователь выбрал задачу для тела"""
    user_id = message.from_user.id
    choice = message.text

    recommendation = format_body_recommendation(choice)
    full_message = f"{recommendation}\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"

    photo_key = "collage_body"
    await send_photo_if_exists(message, photo_key, full_message)

    await message.answer(FINAL_MESSAGE, reply_markup=get_final_menu())
    await state.set_state(UserState.FINAL)

# ========== ВЕТКА "ВОЛОСЫ" - Шаг 1: Тип волос ==========
@router.message(UserState.HAIR_TYPE, F.text.in_([
    "Да, я блондинка",
    "Да, у меня другой цвет (шатенка, русая, рыжая)",
    "Нет, волосы натуральные"
]))
async def hair_type_handler(message: Message, state: FSMContext):
    """Пользователь выбрал тип волос"""
    user_id = message.from_user.id

    if message.text == "Да, я блондинка":
        save_user_data(user_id, "hair_type", "blonde")
    elif message.text == "Да, у меня другой цвет (шатенка, русая, рыжая)":
        save_user_data(user_id, "hair_type", "colored")
    elif message.text == "Нет, волосы натуральные":
        save_user_data(user_id, "hair_type", "natural")

    clear_selected_problems(user_id)

    await state.set_state(UserState.HAIR_PROBLEMS)
    await message.answer(
        "❓ <b>С какими проблемами волос вы сталкиваетесь?</b>\n(можно выбрать несколько)",
        reply_markup=get_hair_problems_menu()
    )

# ========== ВЕТКА "ВОЛОСЫ" - Шаг 2: Проблемы (мультивыбор) ==========
@router.message(UserState.HAIR_PROBLEMS, F.text.in_([
    "Ломкость", "Выпадение", "Перхоть/зуд", "Секущиеся кончики",
    "Тусклость", "Пушистость", "Тонкие и лишенные объема", "Очень поврежденные",
    "Ничего из перечисленного, только общий уход"
]))
async def hair_problems_handler(message: Message, state: FSMContext):
    """Пользователь выбирает/убирает проблемы"""
    user_id = message.from_user.id
    problem = message.text

    current_problems = get_selected_problems(user_id)

    if problem in current_problems:
        remove_selected_problem(user_id, problem)
    else:
        add_selected_problem(user_id, problem)

    updated_problems = get_selected_problems(user_id)

    await message.answer(
        f"✅ <b>Вы выбрали:</b>\n" + "\n".join([f"• {p}" for p in updated_problems]),
        reply_markup=get_hair_problems_menu(updated_problems)
    )

@router.message(UserState.HAIR_PROBLEMS, F.text == "➡️ Продолжить")
async def hair_problems_continue(message: Message, state: FSMContext):
    """Пользователь закончил выбор проблем"""
    user_id = message.from_user.id
    problems = get_selected_problems(user_id)

    if not problems:
        add_selected_problem(user_id, "Общий уход")

    await state.set_state(UserState.HAIR_SCALP)
    await message.answer(
        "❓ <b>Есть ли у вас чувствительная кожа головы?</b>",
        reply_markup=get_yes_no_menu()
    )

# ========== ВЕТКА "ВОЛОСЫ" - Шаг 3: Чувствительная кожа головы ==========
@router.message(UserState.HAIR_SCALP, F.text.in_(["✅ Да", "❌ Нет"]))
async def hair_scalp_handler(message: Message, state: FSMContext):
    """Пользователь ответил про чувствительность кожи головы"""
    user_id = message.from_user.id

    if message.text == "✅ Да":
        save_user_data(user_id, "sensitive_scalp", True)
    else:
        save_user_data(user_id, "sensitive_scalp", False)

    await state.set_state(UserState.HAIR_VOLUME)
    await message.answer(
        "❓ <b>Вам нужен дополнительный акцент на объем?</b>",
        reply_markup=get_yes_no_menu()
    )

# ========== ВЕТКА "ВОЛОСЫ" - Шаг 4: Объем ==========
@router.message(UserState.HAIR_VOLUME, F.text.in_(["✅ Да", "❌ Нет"]))
async def hair_volume_handler(message: Message, state: FSMContext):
    """Пользователь ответил про объем"""
    user_id = message.from_user.id

    if message.text == "✅ Да":
        save_user_data(user_id, "need_volume", True)
    else:
        save_user_data(user_id, "need_volume", False)

    hair_type = get_user_data(user_id, "hair_type")

    if hair_type == "colored":
        await state.set_state(UserState.HAIR_COLOR)
        await message.answer(
            "❓ <b>Уточните, пожалуйста, ваш цвет волос?</b>",
            reply_markup=get_hair_color_menu()
        )
    else:
        await show_hair_recommendation(message, state, user_id)

# ========== ВЕТКА "ВОЛОСЫ" - Шаг 5: Цвет волос (только для окрашенных) ==========
@router.message(UserState.HAIR_COLOR, F.text.in_([
    "Шатенка", "Русая", "Рыжая", "Другой окрашенный цвет"
]))
async def hair_color_handler(message: Message, state: FSMContext):
    """Пользователь выбрал цвет волос"""
    user_id = message.from_user.id
    save_user_data(user_id, "hair_color", message.text)

    await show_hair_recommendation(message, state, user_id)

async def show_hair_recommendation(message: Message, state: FSMContext, user_id):
    """Показать итоговую рекомендацию для волос"""
    recommendation = format_hair_recommendation(user_id)
    full_message = f"{recommendation}\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"

    hair_type = get_user_data(user_id, "hair_type")
    if hair_type == "blonde":
        photo_key = "collage_blonde"
    elif hair_type == "colored":
        photo_key = "collage_colored"
    else:
        photo_key = "collage_natural"

    await send_photo_if_exists(message, photo_key, full_message)

    await message.answer(FINAL_MESSAGE, reply_markup=get_final_menu())
    await state.set_state(UserState.FINAL)

# ========== АДМИН-ПАНЕЛЬ ==========

NAME_TO_KEY = {v: k for k, v in PHOTO_KEYS.items()}
SIMPLIFIED_NAMES = {
    "Молочко для тела": "body_milk",
    "Гидрофильное масло": "hydrophilic_oil",
    "Крем-суфле": "cream_body",
    "Скраб кофе/кокос": "body_scrub",
    "Гель для душа (вишня/манго/лимон)": "shower_gel",
    "Баттер для тела": "body_butter",
    "Гиалуроновая кислота для лица": "hyaluronic_acid",
    "Антицеллюлитный скраб (мята)": "anticellulite_scrub",
    "Биолипидный спрей": "biolipid_spray",
    "Сухое масло спрей": "dry_oil_spray",
    "Масло ELIXIR": "oil_elixir",
    "Молочко для волос": "hair_milk",
    "Масло-концентрат": "oil_concentrate",
    "Флюид для волос": "hair_fluid",
    "Шампунь реконстракт": "reconstruct_shampoo",
    "Маска реконстракт": "reconstruct_mask",
    "Протеиновый крем": "protein_cream",
    "Шампунь для осветленных волос с гиалуроновой кислотой": "blonde_shampoo",
    "Кондиционер для осветленных волос с гиалуроновой кислотой": "blonde_conditioner",
    "Маска для осветленных волос с гиалуроновой кислотой": "blonde_mask",
    "Шампунь для окрашенных волос с коллагеном": "colored_shampoo",
    "Кондиционер для окрашенных волос с коллагеном": "colored_conditioner",
    "Маска для окрашенных волос с коллагеном": "colored_mask",
    "Оттеночная маска Холодный шоколад": "mask_cold_chocolate",
    "Оттеночная маска Медный": "mask_copper",
    "Коллаж для тела": "collage_body",
    "Коллаж для блондинок": "collage_blonde",
    "Коллаж: Окрашенные волосы": "collage_colored",
    "Коллаж: Натуральные волосы": "collage_natural",
    "Коллаж: Ломкость волос": "collage_lomkost",
    "Коллаж: Тусклость": "collage_tusk",
    "Коллаж: Пушистость": "collage_fluffy",
    "Коллаж: Тонкие волосы": "collage_thin",
    "Коллаж: Поврежденные волосы": "collage_damaged",
    "Коллаж: Объем": "collage_volume",
    "Коллаж: Чувствительная кожа головы": "collage_scalp",
    "Коллаж: Выпадение волос": "collage_loss",
    "Коллаж: Перхоть/зуд": "collage_dandruff"
}

@router.message(F.text == "admin2026")
async def admin_access(message: Message, state: FSMContext):
    """Вход в админ-панель"""
    await state.set_state(AdminState.MAIN)
    await message.answer(
        "🔐 <b>Админ-панель активирована!</b>\nВыберите действие:",
        reply_markup=get_admin_main_menu()
    )

@router.message(AdminState.MAIN, F.text == "🔙 Выйти из админки")
async def admin_exit(message: Message, state: FSMContext):
    """Выход из админ-панели"""
    await state.clear()
    await state.set_state(UserState.MAIN_MENU)
    await message.answer(
        "👋 Вы вышли из админ-панели.\nВозвращаюсь в главное меню.",
        reply_markup=get_main_menu()
    )

@router.message(AdminState.MAIN, F.text == "📤 Загрузить фото")
async def admin_upload_start(message: Message, state: FSMContext):
    """Начать загрузку фото"""
    await state.set_state(AdminState.UPLOAD)
    await message.answer(
        "📤 <b>Загрузка фото</b>\nВыберите категорию продукта:",
        reply_markup=get_photo_categories_menu()
    )

@router.message(AdminState.MAIN, F.text == "🗑 Удалить фото")
async def admin_delete_start(message: Message, state: FSMContext):
    """Начать удаление фото"""
    await state.set_state(AdminState.DELETE_SELECT)
    await message.answer(
        "🗑 <b>Удаление фото</b>\nВыберите действие:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🗑 Выбрать для удаления")],
                [KeyboardButton(text="🔙 Назад в админку")]
            ],
            resize_keyboard=True
        )
    )

@router.message(AdminState.MAIN, F.text == "📊 Статус фото")
async def admin_status(message: Message):
    """Показать статус загрузки фото"""
    status = photo_storage.get_photo_status()
    total = len(status)
    uploaded = sum(1 for v in status.values() if v)
    missing = total - uploaded

    response = f"📊 <b>Статус загрузки фото:</b>\n\n"
    response += f"✅ Загружено: {uploaded}/{total}\n"
    response += f"❌ Отсутствует: {missing}\n\n"

    if missing > 0:
        response += "<b>Отсутствующие фото:</b>\n"
        for name, has_photo in status.items():
            if not has_photo:
                response += f"• {name}\n"

    await message.answer(response)

# Обработка выбора категорий фото
@router.message(AdminState.UPLOAD, F.text.in_([
    "🧴 Тело", "💇 Волосы - общие", "👱‍♀️ Блондинки",
    "🎨 Окрашенные", "🎨 Оттеночные маски", "🖼 Коллажи"
]))
async def admin_category_handler(message: Message):
    if message.text == "🧴 Тело":
        await message.answer("Выберите продукт для тела:", reply_markup=get_body_photos_menu())
    elif message.text == "💇 Волосы - общие":
        await message.answer("Выберите общий продукт для волос:", reply_markup=get_hair_common_menu())
    elif message.text == "👱‍♀️ Блондинки":
        await message.answer("Выберите продукт для блондинок:", reply_markup=get_blonde_photos_menu())
    elif message.text == "🎨 Окрашенные":
        await message.answer("Выберите продукт для окрашенных волос:", reply_markup=get_colored_photos_menu())
    elif message.text == "🎨 Оттеночные маски":
        await message.answer("Выберите оттеночную маску:", reply_markup=get_tone_masks_menu())
    elif message.text == "🖼 Коллажи":
        await message.answer("Выберите коллаж:", reply_markup=get_collage_menu())

@router.message(AdminState.UPLOAD, F.text.in_(SIMPLIFIED_NAMES.keys()))
async def admin_select_product(message: Message, state: FSMContext):
    """Выбор конкретного продукта для загрузки"""
    product_name = message.text
    key = SIMPLIFIED_NAMES[product_name]

    await state.update_data(selected_key=key, selected_name=product_name)
    await state.set_state(AdminState.WAITING_PHOTO)

    existing_photo = photo_storage.get_photo_id(key)
    if existing_photo:
        await message.answer(f"📸 <b>{product_name}</b>\nФото уже загружено.\nОтправьте новое фото чтобы заменить существующее:")
    else:
        await message.answer(f"📸 <b>{product_name}</b>\nОтправьте фото продукта:")

@router.message(AdminState.WAITING_PHOTO, F.photo)
async def admin_receive_photo(message: Message, state: FSMContext):
    """Получение и сохранение фото"""
    data = await state.get_data()
    key = data.get("selected_key")
    product_name = data.get("selected_name")

    if not key:
        await message.answer("Ошибка: не выбран продукт")
        await state.set_state(AdminState.UPLOAD)
        await message.answer("Выберите категорию:", reply_markup=get_photo_categories_menu())
        return

    photo = message.photo[-1]
    file_id = photo.file_id

    photo_storage.save_photo_id(key, file_id)

    await message.answer(
        f"✅ <b>Фото успешно загружено!</b>\n"
        f"Продукт: {product_name}\n"
        f"ID фото сохранен в БАЗЕ ДАННЫХ.\n\n"
        f"Продолжайте загрузку или проверьте статус.",
        reply_markup=get_photo_categories_menu()
    )

    await state.set_state(AdminState.UPLOAD)

@router.message(AdminState.WAITING_PHOTO)
async def admin_wrong_input(message: Message):
    await message.answer("❌ Пожалуйста, отправьте фото!")

# Назад в админ-панель
@router.message(AdminState.UPLOAD, F.text == "🔙 Назад")
async def admin_upload_back(message: Message, state: FSMContext):
    await state.set_state(AdminState.MAIN)
    await message.answer("Выберите действие:", reply_markup=get_admin_main_menu())

@router.message(AdminState.UPLOAD, F.text == "🔙 К категориям")
async def admin_back_to_categories(message: Message, state: FSMContext):
    await state.set_state(AdminState.UPLOAD)
    await message.answer("Выберите категорию продукта:", reply_markup=get_photo_categories_menu())

# Удаление фото
@router.message(AdminState.DELETE_SELECT, F.text == "🗑 Выбрать для удаления")
async def admin_delete_select(message: Message):
    all_photos = photo_storage.get_all_photos()
    if not all_photos:
        await message.answer("❌ Нет загруженных фото для удаления.")
        return

    response = "📋 <b>Загруженные фото:</b>\n\n"
    for key, file_id in all_photos.items():
        if key in PHOTO_KEYS:
            product_name = PHOTO_KEYS[key]
            response += f"• {product_name}\n"

    response += "\nВведите точное название продукта для удаления:"
    await message.answer(response)

@router.message(AdminState.DELETE_SELECT, F.text.in_(PHOTO_KEYS.values()))
async def admin_confirm_delete(message: Message, state: FSMContext):
    product_name = message.text
    key = NAME_TO_KEY.get(product_name)

    if not key:
        await message.answer("❌ Продукт не найден в базе.")
        return

    await state.update_data(delete_key=key, delete_name=product_name)
    await state.set_state(AdminState.DELETE_CONFIRM)

    await message.answer(
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"Вы действительно хотите удалить фото для:\n"
        f"<b>{product_name}</b>\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=get_delete_confirmation()
    )

@router.message(AdminState.DELETE_CONFIRM, F.text == "✅ Да, удалить")
async def admin_execute_delete(message: Message, state: FSMContext):
    data = await state.get_data()
    key = data.get("delete_key")
    product_name = data.get("delete_name")

    if key and photo_storage.delete_photo(key):
        await message.answer(
            f"🗑 <b>Фото удалено!</b>\n"
            f"Продукт: {product_name}\n\n"
            f"Выберите следующее действие:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🗑 Выбрать для удаления")],
                    [KeyboardButton(text="🔙 Назад в админку")]
                ],
                resize_keyboard=True
            )
        )
    else:
        await message.answer("❌ Не удалось удалить фото. Возможно, оно уже было удалено.")

    await state.set_state(AdminState.DELETE_SELECT)

@router.message(AdminState.DELETE_CONFIRM, F.text == "❌ Нет, отмена")
async def admin_cancel_delete(message: Message, state: FSMContext):
    await state.set_state(AdminState.DELETE_SELECT)
    await message.answer(
        "Удаление отменено.\nВыберите действие:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🗑 Выбрать для удаления")],
                [KeyboardButton(text="🔙 Назад в админку")]
            ],
            resize_keyboard=True
        )
    )

@router.message(AdminState.DELETE_SELECT, F.text == "🔙 Назад в админку")
async def admin_delete_back(message: Message, state: FSMContext):
    await state.set_state(AdminState.MAIN)
    await message.answer("Выберите действие:", reply_markup=get_admin_main_menu())

# ========== ЗАПУСК БОТА ==========
async def run_bot():
    """Основная функция запуска бота"""
    logger.info(f"🚀 Запуск Telegram бота (экземпляр: {INSTANCE_ID})...")

    # 1. СИЛЬНО УВЕЛИЧЕННАЯ ЗАДЕРЖКА перед запуском (60 секунд!)
    logger.info("⏳ Ожидание 60 секунд для завершения старых процессов...")
    await asyncio.sleep(60)

    # 2. Удаляем вебхук
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Вебхук удален")
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при удалении вебхука: {e}")

    # 3. Дополнительная задержка
    await asyncio.sleep(10)

    print("=" * 50)
    print(f"🤖 БОТ ЗАПУЩЕН (ID: {INSTANCE_ID})")
    print("✅ Диалоговый консультант по косметике")
    print("✅ Фото хранятся в БАЗЕ ДАННЫХ")
    print("✅ Keep-alive система: АКТИВНА")
    print("=" * 50)

    # 4. Запускаем polling
    await dp.start_polling(
        bot,
        skip_updates=True,
        allowed_updates=["message"],
        timeout=30,
        relax=0.5
    )

def signal_handler(sig, frame):
    """Обработчик сигналов для graceful shutdown"""
    print(f'\n⚠️ Получен сигнал остановки (экземпляр: {INSTANCE_ID}). Завершаю работу бота...')
    stop_keep_alive()
    sys.exit(0)

def main():
    """Главная функция"""
    global START_TIME
    START_TIME = time.time()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Запускаем систему keep-alive (пинг каждые 8 минут)
    # Render бесплатный тариф засыпает после 15 минут бездействия
    # 8 минут - безопасный интервал
    start_keep_alive(
        url="https://salon-volosy-beauty10.onrender.com",
        interval=480  # 8 минут = 480 секунд
    )

    http_thread = Thread(target=run_http_server, daemon=True)
    http_thread.start()

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        return 1
    finally:
        # Гарантированно останавливаем keep-alive при выходе
        stop_keep_alive()

    return 0

if __name__ == "__main__":
    sys.exit(main())
import asyncio
import logging
import os
import sys
import signal
import hashlib
import socket
import json
import time
from typing import List
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InputMediaPhoto

from config import BOT_TOKEN, WELCOME_TEXT, LOCATIONS_TEXT, DELIVERY_TEXT, FINAL_MESSAGE
from keyboards import *
from body_data import BODY_DATA
from hair_data import HAIR_DATA
from user_storage import *
from photo_database import photo_storage, PHOTO_KEYS
from states import UserState, AdminState
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
START_TIME = None

class HealthHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP запросов для health checks"""

    def do_GET(self):
        """Обработка GET запросов"""
        if self.path in ['/', '/health', '/ping']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

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
        pass

def run_http_server():
    """Запуск HTTP сервера в отдельном потоке"""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"🌐 HTTP-сервер запущен на порту {port}")
    server.serve_forever()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def find_product_key(product_name):
    """Найти ключ для продукта (гибкий поиск)"""
    # Прямое совпадение
    if product_name in SIMPLIFIED_NAMES:
        return SIMPLIFIED_NAMES[product_name]

    # Поиск по части названия (в обе стороны)
    for name, key in SIMPLIFIED_NAMES.items():
        if product_name.lower() in name.lower() or name.lower() in product_name.lower():
            return key

    # Поиск по ключевым словам
    keywords = product_name.lower().split()
    for name, key in SIMPLIFIED_NAMES.items():
        name_lower = name.lower()
        if any(word in name_lower for word in keywords if len(word) > 3):
            return key

    return None

async def send_product_photos(message: Message, product_keys: List[str], caption: str = ""):
    """Отправить все фото продуктов одним сообщением (медиагруппой)"""
    try:
        media_group = []

        # ДЕТАЛЬНАЯ ОТЛАДКА
        logger.info(f"🖼 Ищем фото для ключей: {product_keys}")

        for i, key in enumerate(product_keys):
            photo_id = photo_storage.get_photo_id(key)
            product_name = PHOTO_KEYS.get(key, key)

            if photo_id:
                logger.info(f"  ✅ [{i+1}] Найдено фото: '{product_name}' (ключ: {key})")
                if not media_group:  # Первое фото получает подпись
                    media_group.append(InputMediaPhoto(media=photo_id, caption=caption, parse_mode="HTML"))
                else:
                    media_group.append(InputMediaPhoto(media=photo_id))

                # Ограничение Telegram: максимум 10 фото в медиагруппе
                if len(media_group) >= 10:
                    logger.warning(f"Достигнут лимит в 10 фото")
                    break
            else:
                logger.warning(f"  ❌ [{i+1}] Фото не найдено: '{product_name}' (ключ: {key})")

        if media_group:
            logger.info(f"✅ Отправляем {len(media_group)} фото в медиагруппе")
            await asyncio.wait_for(
                message.answer_media_group(media_group),
                timeout=30.0
            )
            return True
        else:
            logger.warning("❌ Нет фото для отправки, отправляем только текст")

    except asyncio.TimeoutError:
        logger.error("Таймаут при отправке медиагруппы")
    except Exception as e:
        logger.error(f"Ошибка отправки медиагруппы: {e}", exc_info=True)

    # Если фото нет или ошибка, отправляем только текст
    if caption:
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

# ========== КОНВЕРТЕРЫ ИМЕН ДЛЯ ФОТО ==========
NAME_TO_KEY = {v: k for k, v in PHOTO_KEYS.items()}

SIMPLIFIED_NAMES = {
    # ========== ТЕЛО ==========
    "Молочко для тела": "body_milk",
    "Гидрофильное масло": "hydrophilic_oil",
    "Крем-суфле": "cream_body",
    "Скраб кофе/кокос": "body_scrub",
    "Гель для душа (вишня/манго/лимон)": "shower_gel",
    "Баттер для тела": "body_butter",
    "Гиалуроновая кислота для лица": "hyaluronic_acid",
    "Антицеллюлитный скраб (мята)": "anticellulite_scrub",

    # ========== ВОЛОСЫ - ОБЩИЕ ==========
    "Биолипидный спрей": "biolipid_spray",
    "Сухое масло спрей": "dry_oil_spray",
    "Масло ELIXIR": "oil_elixir",
    "Молочко для волос": "hair_milk",
    "Масло-концентрат": "oil_concentrate",
    "Флюид для волос": "hair_fluid",
    "Шампунь реконстракт": "reconstruct_shampoo",
    "Маска реконстракт": "reconstruct_mask",
    "Протеиновый крем": "protein_cream",

    # ========== БЛОНДИНКИ ==========
    "Шампунь для осветленных волос с гиалуроновой кислотой": "blonde_shampoo",
    "Кондиционер для осветленных волос с гиалуроновой кислотой": "blonde_conditioner",
    "Маска для осветленных волос с гиалуроновой кислотой": "blonde_mask",

    # ========== ОКРАШЕННЫЕ ==========
    "Шампунь для окрашенных волос с коллагеном": "colored_shampoo",
    "Кондиционер для окрашенных волос с коллагеном": "colored_conditioner",
    "Маска для окрашенных волос с коллагеном": "colored_mask",

    # ========== ОТТЕНОЧНЫЕ МАСКИ ==========
    "Оттеночная маска Холодный шоколад": "mask_cold_chocolate",
    "Оттеночная маска Медный": "mask_copper",
}

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

    if current_state not in [AdminState.MAIN, AdminState.UPLOAD, AdminState.WAITING_PHOTO,
                            AdminState.DELETE_SELECT, AdminState.DELETE_CONFIRM]:
        await state.set_state(UserState.HAIR_TYPE)
        await message.answer(
            "❓ <b>Ваши волосы окрашены?</b>",
            reply_markup=get_hair_type_menu()
        )

# Финальные кнопки
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

    # Собираем ключи фото для продуктов тела
    body_data = BODY_DATA[choice]
    product_keys = []

    # Преобразуем названия продуктов в ключи
    for product in body_data["products"]:
        key = find_product_key(product)
        if key:
            product_keys.append(key)
            logger.info(f"✅ Тело: '{product}' -> ключ: {key}")
        else:
            logger.warning(f"❌ Тело: не найден ключ для продукта: '{product}'")

    # Добавляем гиалуроновую кислоту (из note)
    note = body_data["note"]
    if "гиалуроновая кислота" in note.lower():
        key = find_product_key("Гиалуроновая кислота для лица")
        if key:
            product_keys.append(key)
            logger.info(f"✅ Добавлена гиалуроновая кислота -> ключ: {key}")

    # Удаляем дубликаты
    unique_keys = list(set(product_keys))
    logger.info(f"📦 Тело: итоговые ключи для поиска фото: {unique_keys}")

    # Отправляем фото продуктов
    await send_product_photos(message, unique_keys, full_message)

    await message.answer(FINAL_MESSAGE, reply_markup=get_final_menu())
    await state.set_state(UserState.FINAL)

# ========== ВЕТКА "ВОЛОСЫ" ==========
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

    # Собираем ключи фото для всех продуктов в рекомендации
    product_keys = []
    user_data = get_user_data(user_id)
    hair_type = user_data.get("hair_type")
    problems = get_selected_problems(user_id)
    sensitive_scalp = user_data.get("sensitive_scalp", False)
    need_volume = user_data.get("need_volume", False)
    hair_color = user_data.get("hair_color")

    # ДОБАВЬТЕ ЭТУ ОТЛАДКУ:
    logger.info("=" * 50)
    logger.info("🔍 ФОРМИРУЕМ СПИСОК ПРОДУКТОВ ДЛЯ ФОТО")

    # Базовый уход
    if hair_type in HAIR_DATA["base_care"]:
        logger.info(f"📝 Базовый уход для типа '{hair_type}':")
        for product in HAIR_DATA["base_care"][hair_type]["products"]:
            key = find_product_key(product)
            if key:
                product_keys.append(key)
                logger.info(f"  ✅ '{product}' -> ключ: {key}")
            else:
                logger.warning(f"  ❌ Не найден ключ для продукта: '{product}'")

    # Проблемы
    if problems and "Общий уход" not in problems:
        logger.info(f"📝 Проблемы: {problems}")
        for problem in problems:
            if problem in HAIR_DATA["problems"]:
                logger.info(f"  📝 Обрабатываем проблему: '{problem}'")
                for product in HAIR_DATA["problems"][problem]["products"]:
                    key = find_product_key(product)
                    if key:
                        product_keys.append(key)
                        logger.info(f"    ✅ '{product}' -> ключ: {key}")
                    else:
                        logger.warning(f"    ❌ Не найден ключ для продукта: '{product}'")

    # Чувствительная кожа головы
    if sensitive_scalp:
        logger.info("📝 Чувствительная кожа головы:")
        for product in HAIR_DATA["scalp"]["products"]:
            key = find_product_key(product)
            if key:
                product_keys.append(key)
                logger.info(f"  ✅ '{product}' -> ключ: {key}")
            else:
                logger.warning(f"  ❌ Не найден ключ для продукта: '{product}'")

    # Объем
    if need_volume:
        logger.info("📝 Объем:")
        for product in HAIR_DATA["volume"]["products"]:
            key = find_product_key(product)
            if key:
                product_keys.append(key)
                logger.info(f"  ✅ '{product}' -> ключ: {key}")
            else:
                logger.warning(f"  ❌ Не найден ключ для продукта: '{product}'")

    # Оттеночные маски
    if hair_type == "colored" and hair_color and hair_color in HAIR_DATA["color_masks"]:
        color_mask = HAIR_DATA["color_masks"][hair_color]
        logger.info(f"📝 Оттеночная маска для '{hair_color}': '{color_mask}'")
        key = find_product_key(color_mask)
        if key:
            product_keys.append(key)
            logger.info(f"  ✅ '{color_mask}' -> ключ: {key}")
        else:
            logger.warning(f"  ❌ Не найден ключ для оттеночной маски: '{color_mask}'")

    # Удаляем дубликаты
    unique_keys = list(set(product_keys))
    logger.info(f"📦 Итоговые ключи для поиска фото: {unique_keys}")
    logger.info("=" * 50)

    # Отправляем фото продуктов
    await send_product_photos(message, unique_keys, full_message)

    await message.answer(FINAL_MESSAGE, reply_markup=get_final_menu())
    await state.set_state(UserState.FINAL)

# ========== ОТЛАДОЧНЫЕ КОМАНДЫ ==========
@router.message(F.text == "/checkphotos")
async def check_photos_command(message: Message):
    """Команда для проверки загруженных фото"""
    all_photos = photo_storage.get_all_photos()

    if not all_photos:
        await message.answer("❌ В базе нет ни одного фото!")
        return

    response = "📋 <b>Загруженные фото в базе:</b>\n\n"
    for key, file_id in all_photos.items():
        product_name = PHOTO_KEYS.get(key, key)
        response += f"• <b>{product_name}</b>\n"
        response += f"  Ключ: <code>{key}</code>\n"
        response += f"  ID: <code>{file_id[:30]}...</code>\n\n"

    await message.answer(response)

@router.message(F.text.startswith("/check "))
async def check_product_photo(message: Message):
    """Проверить фото конкретного продукта"""
    product_name = message.text.replace("/check ", "").strip()

    # Ищем ключ
    key = find_product_key(product_name)

    if not key:
        await message.answer(f"❌ Продукт '{product_name}' не найден в SIMPLIFIED_NAMES")
        return

    photo_id = photo_storage.get_photo_id(key)

    if photo_id:
        await message.answer(
            f"✅ <b>{product_name}</b>\n"
            f"Ключ: <code>{key}</code>\n"
            f"File ID: <code>{photo_id[:50]}...</code>\n\n"
            f"Фото загружено в базу!"
        )
        # Отправляем фото для проверки
        try:
            await message.answer_photo(photo_id, caption=f"Тестовое фото: {product_name}")
        except Exception as e:
            await message.answer(f"⚠️ Не удалось отправить фото: {e}")
    else:
        await message.answer(
            f"❌ <b>{product_name}</b>\n"
            f"Ключ: <code>{key}</code>\n"
            f"Фото НЕ загружено в базу!\n\n"
            f"Загрузите фото через админ-панель."
        )

@router.message(F.text == "/debug")
async def debug_info(message: Message):
    """Отладочная информация"""
    response = f"🤖 <b>Отладочная информация:</b>\n\n"
    response += f"ID экземпляра: <code>{INSTANCE_ID}</code>\n"
    response += f"Всего фото в системе: {len(PHOTO_KEYS)}\n"

    # Проверяем примеры
    test_products = [
        "Шампунь для окрашенных волос с коллагеном",
        "Кондиционер для окрашенных волос с коллагеном",
        "Маска для окрашенных волос с коллагеном",
        "Биолипидный спрей"
    ]

    response += "\n<b>Проверка ключей:</b>\n"
    for product in test_products:
        key = find_product_key(product)
        has_photo = "✅ Есть" if photo_storage.get_photo_id(key) else "❌ Нет"
        response += f"• {product}: <code>{key}</code> - {has_photo}\n"

    await message.answer(response)

# ========== АДМИН-ПАНЕЛЬ ==========

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
                [KeyboardButton(text="👁 Просмотреть фото")],
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

# ========== ЗАГРУЗКА ФОТО ==========
@router.message(AdminState.UPLOAD, F.text.in_([
    "🧴 Тело", "💇 Волосы - общие", "👱‍♀️ Блондинки",
    "🎨 Окрашенные", "🎨 Оттеночные маски"
]))
async def admin_category_handler(message: Message, state: FSMContext):
    """Обработка выбора категории для загрузки фото"""
    logger.info(f"📁 Категория выбрана: {message.text}, состояние: {await state.get_state()}")

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

@router.message(AdminState.UPLOAD, F.text.in_(SIMPLIFIED_NAMES.keys()))
async def admin_select_product(message: Message, state: FSMContext):
    """Выбор конкретного продукта для загрузки"""
    product_name = message.text
    key = SIMPLIFIED_NAMES.get(product_name)

    logger.info(f"🎯 Выбран продукт: {product_name}, ключ: {key}")

    if not key:
        await message.answer(f"❌ Ошибка: продукт '{product_name}' не найден в базе.")
        return

    await state.update_data(selected_key=key, selected_name=product_name)
    await state.set_state(AdminState.WAITING_PHOTO)

    existing_photo = photo_storage.get_photo_id(key)
    if existing_photo:
        await message.answer(
            f"📸 <b>{product_name}</b>\n"
            f"Фото уже загружено.\n"
            f"Отправьте новое фото чтобы заменить существующее:"
        )
    else:
        await message.answer(f"📸 <b>{product_name}</b>\nОтправьте фото продукта:")

@router.message(AdminState.WAITING_PHOTO, F.photo)
async def admin_receive_photo(message: Message, state: FSMContext):
    """Получение и сохранение фото"""
    data = await state.get_data()
    key = data.get("selected_key")
    product_name = data.get("selected_name")

    if not key:
        await message.answer("❌ Ошибка: не выбран продукт")
        await state.set_state(AdminState.UPLOAD)
        await message.answer("Выберите категорию:", reply_markup=get_photo_categories_menu())
        return

    photo = message.photo[-1]
    file_id = photo.file_id

    success = photo_storage.save_photo_id(key, file_id)

    if success:
        await message.answer(
            f"✅ <b>Фото успешно загружено!</b>\n"
            f"Продукт: {product_name}\n"
            f"ID фото сохранен в БАЗЕ ДАННЫХ.\n\n"
            f"Продолжайте загрузку или проверьте статус.",
            reply_markup=get_photo_categories_menu()
        )
    else:
        await message.answer(
            f"❌ <b>Ошибка при сохранении фото!</b>\n"
            f"Продукт: {product_name}\n"
            f"Ключ: {key}\n\n"
            f"Попробуйте еще раз.",
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

# ========== УДАЛЕНИЕ И ПРОСМОТР ФОТО ==========
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

@router.message(AdminState.DELETE_SELECT, F.text == "👁 Просмотреть фото")
async def admin_view_photos(message: Message):
    """Просмотр загруженных фото"""
    all_photos = photo_storage.get_all_photos()

    if not all_photos:
        await message.answer("❌ Нет загруженных фото для просмотра.")
        return

    # Создаем медиагруппу из всех фото (не более 10)
    media_group = []
    for i, (key, file_id) in enumerate(all_photos.items()):
        if i >= 10:  # Ограничение Telegram
            break

        product_name = PHOTO_KEYS.get(key, key)
        if not media_group:  # Первое фото получает подпись
            media_group.append(InputMediaPhoto(
                media=file_id, 
                caption=f"📸 <b>Загруженные фото</b>\nВсего: {len(all_photos)}",
                parse_mode="HTML"
            ))
        else:
            media_group.append(InputMediaPhoto(media=file_id))

    try:
        await message.answer_media_group(media_group)
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке фото: {e}\n\nПопробуйте посмотреть фото по одному.")

        # Альтернатива: отправляем по одному
        for key, file_id in list(all_photos.items())[:5]:  # Первые 5
            product_name = PHOTO_KEYS.get(key, key)
            try:
                await message.answer_photo(file_id, caption=f"📸 {product_name}")
                await asyncio.sleep(1)  # Задержка чтобы не превысить лимиты
            except:
                continue

@router.message(AdminState.DELETE_SELECT, F.text.in_(PHOTO_KEYS.values()))
async def admin_confirm_delete(message: Message, state: FSMContext):
    product_name = message.text
    key = NAME_TO_KEY.get(product_name)

    if not key:
        await message.answer("❌ Продукт не найден в базе.")
        return

    # Сначала показываем фото, если оно есть
    photo_id = photo_storage.get_photo_id(key)
    if photo_id:
        try:
            await message.answer_photo(photo_id, caption=f"📸 <b>{product_name}</b>")
        except Exception as e:
            await message.answer(f"⚠️ Не удалось показать фото: {e}")

    await state.update_data(delete_key=key, delete_name=product_name)
    await state.set_state(AdminState.DELETE_CONFIRM)

    if photo_id:
        await message.answer(
            f"⚠️ <b>Подтверждение удаления</b>\n\n"
            f"Вы действительно хотите удалить фото для:\n"
            f"<b>{product_name}</b>\n\n"
            f"Это действие нельзя отменить!",
            reply_markup=get_delete_confirmation()
        )
    else:
        await message.answer(
            f"⚠️ <b>Подтверждение удаления</b>\n\n"
            f"Фото для <b>{product_name}</b> не найдено.\n"
            f"Вы хотите очистить запись в базе данных?\n\n"
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
                    [KeyboardButton(text="👁 Просмотреть фото")],
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
                [KeyboardButton(text="👁 Просмотреть фото")],
                [KeyboardButton(text="🔙 Назад в админку")]
            ],
            resize_keyboard=True
        )
    )

@router.message(AdminState.DELETE_SELECT, F.text == "🔙 Назад в админку")
async def admin_delete_back(message: Message, state: FSMContext):
    await state.set_state(AdminState.MAIN)
    await message.answer("Выберите действие:", reply_markup=get_admin_main_menu())

# ========== ДОПОЛНИТЕЛЬНЫЙ ХЭНДЛЕР ДЛЯ ОТЛАДКИ ==========
@router.message(AdminState.UPLOAD)
async def admin_upload_debug(message: Message, state: FSMContext):
    """Отладочный хэндлер для всех сообщений в AdminState.UPLOAD"""
    logger.info(f"DEBUG AdminState.UPLOAD: текст='{message.text}', состояние={await state.get_state()}")
    await message.answer(
        f"ℹ️ Вы в режиме загрузки фото.\n"
        f"Выберите категорию из меню:",
        reply_markup=get_photo_categories_menu()
    )

# ========== ЗАПУСК БОТА ==========
async def run_bot():
    """Основная функция запуска бота"""
    logger.info(f"🚀 Запуск Telegram бота (экземпляр: {INSTANCE_ID})...")

    await asyncio.sleep(10)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Вебхук удален")
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при удалении вебхука: {e}")

    await asyncio.sleep(5)

    print("=" * 50)
    print(f"🤖 БОТ ЗАПУЩЕН (ID: {INSTANCE_ID})")
    print("✅ Диалоговый консультант по косметике")
    print("✅ Фото хранятся в БАЗЕ ДАННЫХ")
    print("✅ Keep-alive система: АКТИВНА")
    print("✅ Отладочные команды: /checkphotos, /debug, /check [продукт]")
    print("=" * 50)

    await dp.start_polling(
        bot,
        skip_updates=True,
        allowed_updates=["message"],
        timeout=30,
        relax=0.5
    )

def signal_handler(sig, frame):
    print(f'\n⚠️ Получен сигнал остановки (экземпляр: {INSTANCE_ID}). Завершаю работу бота...')
    stop_keep_alive()
    sys.exit(0)

def main():
    global START_TIME
    START_TIME = time.time()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    start_keep_alive(
        url="https://salon-volosy-beauty11.onrender.com",
        interval=480
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
        stop_keep_alive()

    return 0

if __name__ == "__main__":
    sys.exit(main())
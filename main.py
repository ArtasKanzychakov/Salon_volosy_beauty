import asyncio
import logging
import os
import sys
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from config import BOT_TOKEN, WELCOME_TEXT, LOCATIONS_TEXT, DELIVERY_TEXT
from keyboards import *
from body_data import BODY_DATA
from hair_data import HAIR_DATA
from user_storage import *
from photo_storage import photo_storage, PHOTO_KEYS

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

class AdminState(StatesGroup):
    MAIN = State()
    UPLOAD = State()
    WAITING_PHOTO = State()
    DELETE_SELECT = State()
    DELETE_CONFIRM = State()

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def format_response(data):
    """Форматирует ответ с продуктами"""
    response = f"{data['title']}\n\n"
    for product in data["products"]:
        response += f"• {product}\n"
    if "note" in data:
        response += f"\n<b>{data['note']}</b>\n"
    return response

async def send_photo_if_exists(message: Message, photo_key: str, caption: str):
    """Отправить фото, если оно есть в хранилище"""
    if photo_key:
        photo_id = photo_storage.get_photo_id(photo_key)
        if photo_id:
            await message.answer_photo(photo_id, caption=caption, parse_mode="HTML")
            return True
    
    # Если фото нет, отправляем только текст
    await message.answer(caption, parse_mode="HTML")
    return False

# ========== ОБРАБОТЧИКИ КОМАНД ==========

# Старт
@router.message(F.text == "/start")
@router.message(F.text == "🔄 Новый подбор")
async def cmd_start(message: Message, state: FSMContext):
    clear_user_data(message.from_user.id)
    clear_selected_problems(message.from_user.id)
    await state.clear()
    await state.set_state(UserState.MAIN_MENU)
    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu())

# Назад
@router.message(F.text == "◀️ Назад")
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
        hair_type = get_user_data(user_id, "hair_type")
        if hair_type == "colored":
            await state.set_state(UserState.HAIR_COLOR)
            await message.answer("Выберите цвет окрашенных волос:", reply_markup=get_hair_color_menu())
        else:
            await state.set_state(UserState.HAIR_TYPE)
            await message.answer("Выберите тип ваших волос:", reply_markup=get_hair_type_menu())
    elif current_state == UserState.HAIR_PROBLEMS:
        await state.set_state(UserState.HAIR_CARE)
        await message.answer("Выберите категорию ухода:", reply_markup=get_hair_care_menu())
    else:
        await cmd_start(message, state)

# Главное меню
@router.message(UserState.MAIN_MENU, F.text == "🧴 Тело")
async def body_handler(message: Message, state: FSMContext):
    await state.set_state(UserState.BODY_MENU)
    await message.answer("Выберите тип ухода за телом:", reply_markup=get_body_menu())

@router.message(UserState.MAIN_MENU, F.text == "💇 Волосы")
async def hair_handler(message: Message, state: FSMContext):
    await state.set_state(UserState.HAIR_TYPE)
    await message.answer("Выберите тип ваших волос:", reply_markup=get_hair_type_menu())

# Финальные кнопки (работают из любого состояния)
@router.message(F.text.in_(["📍 Точки", "🚚 Доставка"]))
async def final_buttons_handler(message: Message, state: FSMContext):
    if message.text == "📍 Точки":
        await message.answer(LOCATIONS_TEXT, reply_markup=get_final_menu())
    elif message.text == "🚚 Доставка":
        await message.answer(DELIVERY_TEXT, reply_markup=get_final_menu())

# ========== ОБРАБОТКА ТЕЛА ==========
@router.message(UserState.BODY_MENU, F.text.in_(BODY_DATA))
async def body_recommendation_handler(message: Message, state: FSMContext):
    choice = message.text
    data = BODY_DATA[choice]
    
    response = format_response(data)
    response += f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"
    
    # Отправляем с фото
    photo_key = data.get("photo_key")
    await send_photo_if_exists(message, photo_key, response)
    
    # ОСТАЁМСЯ в меню тела, показываем меню снова
    await message.answer("Выберите другой тип ухода за телом:", reply_markup=get_body_menu())

# ========== ОБРАБОТКА ВОЛОС ==========

# Выбор типа волос
@router.message(UserState.HAIR_TYPE, F.text.in_([
    "👱‍♀️ Блондинки (окрашенные)",
    "🎨 Окрашенные волосы",
    "🌿 Натуральные волосы"
]))
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
@router.message(UserState.HAIR_COLOR, F.text.in_(["Шатенка/Русая", "Рыжая"]))
async def hair_color_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    save_user_data(user_id, "hair_color", message.text)
    await state.set_state(UserState.HAIR_CARE)
    await message.answer("Выберите категорию ухода:", reply_markup=get_hair_care_menu())

# Выбор категории ухода для волос
@router.message(UserState.HAIR_CARE, F.text.in_([
    "🧴 Общий уход", "⚡ Специфические проблемы",
    "❤️ Чувствительная кожа головы", "💨 Объем"
]))
async def hair_category_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    hair_type = get_user_data(user_id, "hair_type")
    hair_color = get_user_data(user_id, "hair_color")
    
    if message.text == "🧴 Общий уход":
        if hair_type == "colored":
            if hair_color == "Шатенка/Русая":
                data = HAIR_DATA[hair_type]["colors"]["шатенка/русая"]["general"]
                photo_key = data.get("photo_key")
            elif hair_color == "Рыжая":
                data = HAIR_DATA[hair_type]["colors"]["рыжая"]["general"]
                photo_key = data.get("photo_key")
        else:
            data = HAIR_DATA[hair_type]["general"]
            photo_key = data.get("photo_key")
        
        response = format_response(data)
        response += f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"
        
        # Отправляем с фото
        await send_photo_if_exists(message, photo_key, response)
        # ОСТАЁМСЯ в меню ухода, показываем его снова
        await message.answer("Выберите другую категорию ухода:", reply_markup=get_hair_care_menu())
    
    elif message.text == "⚡ Специфические проблемы":
        await state.set_state(UserState.HAIR_PROBLEMS)
        await message.answer("Выберите конкретную проблему:", reply_markup=get_hair_problems_menu())
    
    elif message.text == "❤️ Чувствительная кожа головы":
        data = HAIR_DATA[hair_type]["scalp"]
        response = format_response(data)
        response += f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"
        
        photo_key = data.get("photo_key")
        await send_photo_if_exists(message, photo_key, response)
        # ОСТАЁМСЯ в меню ухода, показываем его снова
        await message.answer("Выберите другую категорию ухода:", reply_markup=get_hair_care_menu())
    
    elif message.text == "💨 Объем":
        data = HAIR_DATA[hair_type]["volume"]
        response = format_response(data)
        response += f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"
        
        photo_key = data.get("photo_key")
        await send_photo_if_exists(message, photo_key, response)
        # ОСТАЁМСЯ в меню ухода, показываем его снова
        await message.answer("Выберите другую категорию ухода:", reply_markup=get_hair_care_menu())

# Выбор конкретной проблемы
@router.message(UserState.HAIR_PROBLEMS, F.text.in_([
    "Ломкость", "Выпадение", "Перхоть/зуд", "Секущиеся кончики",
    "Тусклость", "Пушистость", "Тонкие", "Очень поврежденные"
]))
async def hair_problem_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    hair_type = get_user_data(user_id, "hair_type")
    problem = message.text
    
    if hair_type and problem in HAIR_DATA[hair_type]["problems"]:
        data = HAIR_DATA[hair_type]["problems"][problem]
        response = format_response(data)
        response += f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}"
        
        photo_key = data.get("photo_key")
        await send_photo_if_exists(message, photo_key, response)
        # ВОЗВРАЩАЕМСЯ в меню ухода, показываем его
        await state.set_state(UserState.HAIR_CARE)
        await message.answer("Выберите категорию ухода:", reply_markup=get_hair_care_menu())

# ========== АДМИН-ПАНЕЛЬ ==========

# Словарь для преобразования русских названий в ключи фото
NAME_TO_KEY = {v: k for k, v in PHOTO_KEYS.items()}
SIMPLIFIED_NAMES = {
    # 🧴 ТЕЛО
    "Молочко для тела": "body_milk",
    "Гидрофильное масло": "hydrophilic_oil",
    "Крем суфле": "cream_body",
    "Скраб кофе/кокос": "body_scrub",
    "Гель для душа вишня/манго/лимон": "shower_gel",
    "Баттер для тела": "body_butter",
    "Гиалуроновая кислота для лица": "hyaluronic_acid",
    
    # 💇 ВОЛОСЫ - ОБЩИЕ
    "Биолипидный спрей": "biolipid_spray",
    "Сухое масло спрей": "dry_oil_spray",
    "масло ELIXIR": "oil_elixir",
    "Молочко для волос": "hair_milk",
    "масло концентрат": "oil_concentrate",
    "Флюид для волос": "hair_fluid",
    "Шампунь реконстракт": "reconstruct_shampoo",
    "Маска реконстракт": "reconstruct_mask",
    "Протеиновый крем": "protein_cream",
    
    # 👱‍♀️ БЛОНДИНКИ
    "Шампунь для осветленных волос с гиалуроновой кислотой": "blonde_shampoo",
    "Кондиционер для осветленных волос с гиалуроновой кислотой": "blonde_conditioner",
    "Маска для осветленных волос с гиалуроновой кислотой": "blonde_mask",
    
    # 🎨 ОКРАШЕННЫЕ
    "Шампунь для окрашенных волос с коллагеном": "colored_shampoo",
    "Кондиционер для окрашенных волос с коллагеном": "colored_conditioner",
    "Маска для окрашенных волос с коллагеном": "colored_mask",
    
    # 🎨 ОТТЕНОЧНЫЕ МАСКИ
    "Оттеночная маска Холодный шоколад": "mask_cold_chocolate",
    "Оттеночная маска Медный": "mask_copper",
    "Оттеночная маска Розовая пудра": "mask_pink_powder",
    "Оттеночная маска Перламутр": "mask_mother_of_pearl",
    
    # 🖼 КОЛЛАЖИ
    "Коллаж для блондинок (общий уход)": "blonde_general",
    "Коллаж: Ломкость волос": "blonde_lomkost",
    "Коллаж: Тусклость": "hair_milk_concentrate",
    "Коллаж: Пушистость": "fluid_protein_elixir",
    "Коллаж: Тонкие волосы": "thin_hair_care",
    "Коллаж: Поврежденные волосы": "damaged_hair",
    "Коллаж: Окрашенные (шатен/русая)": "colored_general_chocolate",
    "Коллаж: Окрашенные (рыжая)": "colored_general_copper",
    "Коллаж: Натуральные волосы": "natural_general",
    "Коллаж: Объем": "volume_care",
    "Коллаж: Чувствительная кожа головы": "sensitive_scalp",
    "Коллаж: Выпадение волос": "hair_loss",
    "Коллаж: Перхоть/зуд": "dandruff",
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
        f"ID фото сохранен в базе.\n\n"
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
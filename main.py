"""
MAIN.PY - Бот с массовой загрузкой фото через админ-панель
Обновлено для работы на Render Free
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import List, Dict
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from states import UserState, AdminState
import keyboards
import photo_map
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

# ==================== HEALTH CHECK SERVER ====================

class HealthHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP запросов для health check"""
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>Bot is running!</h1>')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Отключаем стандартное логирование запросов в консоль
        pass

def run_health_server():
    """Запуск HTTP сервера для health check"""
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"🌐 Health check сервер запущен на порту {port}")
    server.serve_forever()

def start_health_server():
    """Запуск health check сервера в отдельном потоке"""
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    logger.info("🔔 Health check система активирована")

# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ====================

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

async def send_recommended_photos(chat_id: int, photo_keys: List[str], caption: str = ""):
    """Отправка рекомендованных фото"""
    try:
        if not photo_keys:
            await bot.send_message(
                chat_id, 
                "📷 Фото продуктов пока не загружены.",
                reply_markup=keyboards.selection_complete_keyboard()
            )
            return

        sent_count = 0
        missing_products = []
        
        for photo_key in photo_keys:
            file_id = photo_map.get_photo_file_id(photo_key)
            if file_id:
                # Находим отображаемое имя
                display_name = photo_key
                
                # Ищем отображаемое имя в структуре
                for category_data in config.PHOTO_STRUCTURE_ADMIN.values():
                    for subcat_products in category_data.values():
                        for key, name in subcat_products:
                            if key == photo_key:
                                display_name = name
                                break
                
                # Получаем цену из конфига
                price = config.PRODUCT_PRICES.get(photo_key, "")
                
                # Формируем подпись
                if caption:
                    caption_text = f"{caption}\n<b>{display_name}</b>"
                else:
                    caption_text = f"<b>{display_name}</b>"
                
                if price:
                    caption_text += f"\n💰 Цена: {price}"
                
                # Отправляем фото
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption=caption_text,
                    parse_mode=ParseMode.HTML
                )
                sent_count += 1
                await asyncio.sleep(0.2)  # Небольшая задержка между фото
            else:
                # Запоминаем отсутствующие продукты
                for category_data in config.PHOTO_STRUCTURE_ADMIN.values():
                    for subcat_products in category_data.values():
                        for key, name in subcat_products:
                            if key == photo_key:
                                missing_products.append(name)
                                break

        # Если не все фото загружены - показываем сообщение
        if missing_products:
            await bot.send_message(
                chat_id,
                f"📷 <i>Примечание: отсутствуют фото для {len(missing_products)} продуктов.\n"
                f"Администратор скоро добавит недостающие фотографии!</i>",
                reply_markup=keyboards.selection_complete_keyboard()
            )
        elif sent_count == 0:
            await bot.send_message(
                chat_id,
                "📷 Фото продуктов пока не загружены.\n"
                "Администратор скоро добавит фотографии!",
                reply_markup=keyboards.selection_complete_keyboard()
            )
        else:
            # Все фото отправлены успешно
            pass

    except Exception as e:
        logger.error(f"❌ Ошибка при отправке фото: {e}", exc_info=True)
        await bot.send_message(
            chat_id,
            "❌ Произошла ошибка при отправке фото.",
            reply_markup=keyboards.selection_complete_keyboard()
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

        # Добавляем фото по типу волос
        if hair_type in config.PHOTO_MAPPING.get("волосы", {}):
            photo_keys.extend(config.PHOTO_MAPPING["волосы"][hair_type])

        # Добавляем фото по проблемам
        for problem in problems:
            if problem in config.PHOTO_MAPPING.get("волосы", {}):
                photo_keys.extend(config.PHOTO_MAPPING["волосы"][problem])

        # Добавляем фото для чувствительной кожи
        if scalp_type == "Да, чувствительная":
            sensitive_keys = config.PHOTO_MAPPING["волосы"].get("чувствительная_кожа", [])
            photo_keys.extend(sensitive_keys)

        # Добавляем фото для объема
        if hair_volume == "Да, хочу объем":
            volume_keys = config.PHOTO_MAPPING["волосы"].get("объем", [])
            photo_keys.extend(volume_keys)

        # Добавляем фото по цвету волос
        if hair_color in ["Шатенка", "Русая"]:
            chocolate_keys = config.PHOTO_MAPPING["волосы"].get("оттеночная_шоколад", [])
            photo_keys.extend(chocolate_keys)
        elif hair_color == "Рыжая":
            copper_keys = config.PHOTO_MAPPING["волосы"].get("оттенечная_медный", [])
            photo_keys.extend(copper_keys)

        # Убираем дубликаты
        photo_keys = list(set(photo_keys))
        return text, photo_keys

    except Exception as e:
        logger.error(f"❌ Ошибка получения рекомендаций для волос: {e}")
        return "Рекомендации временно недоступны.", []

def format_photo_stats() -> str:
    """Форматирование статистики фото"""
    stats = photo_map.get_photo_stats()

    text = (
        f"📊 <b>Статистика загруженных фото</b>\n\n"
        f"✅ <b>Загружено:</b> {stats['loaded']} из {stats['total']}\n"
        f"📈 <b>Прогресс:</b> {stats['percentage']}%\n"
        f"❌ <b>Осталось:</b> {stats['missing']} фото\n\n"
    )

    if stats['percentage'] < 30:
        text += "⚠️ <i>Загружено очень мало фото. Рекомендуется загрузить основные продукты.</i>"
    elif stats['percentage'] < 70:
        text += "🔄 <i>Продолжайте загрузку для полного покрытия.</i>"
    else:
        text += "✅ <i>Большинство фото загружено. Отличная работа!</i>"

    # Показываем отсутствующие фото
    missing_photos = photo_map.get_missing_photos()
    missing_list = [p for p in missing_photos if p["status"] == "❌ Отсутствует"]
    
    if missing_list:
        text += f"\n\n<b>Отсутствуют фото для:</b>\n"
        for i, photo in enumerate(missing_list[:5]):  # Показываем первые 5
            text += f"{i+1}. {photo['name']}\n"
        if len(missing_list) > 5:
            text += f"... и еще {len(missing_list) - 5} продуктов"

    return text

def format_photo_list(photos: List[Dict], page: int, filter_type: str = "all") -> str:
    """Форматирование списка фото для отображения"""
    per_page = config.ADMIN_PHOTOS_PER_PAGE
    start_idx = page * per_page
    end_idx = start_idx + per_page

    filtered_photos = photos
    if filter_type == "missing":
        filtered_photos = [p for p in photos if p["status"] == "❌ Отсутствует"]
    elif filter_type == "loaded":
        filtered_photos = [p for p in photos if p["status"] == "✅ Загружено"]

    current_photos = filtered_photos[start_idx:end_idx]

    # Заголовок
    if filter_type == "all":
        title = "📋 <b>Все фото</b>"
    elif filter_type == "loaded":
        title = "✅ <b>Загруженные фото</b>"
    else:
        title = "❌ <b>Отсутствующие фото</b>"

    text = f"{title}\n"
    text += f"Страница {page + 1} из {(len(filtered_photos) + per_page - 1) // per_page}\n\n"

    for i, photo in enumerate(current_photos, start=start_idx + 1):
        file_id_preview = photo["file_id"][:20] + "..." if photo["file_id"] else "нет"
        text += f"{i}. {photo['status']} <b>{photo['name']}</b>\n"
        text += f"   Ключ: <code>{photo['key']}</code>\n"
        if photo["file_id"]:
            text += f"   file_id: <code>{file_id_preview}</code>\n"
        
        # Добавляем цену если есть
        price = config.PRODUCT_PRICES.get(photo['key'], "")
        if price:
            text += f"   💰 Цена: {price}\n"
            
        text += "\n"

    stats = photo_map.get_photo_stats()
    text += f"\n📈 <b>Итого:</b> {stats['loaded']}/{stats['total']} ({stats['percentage']}%)"

    return text

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
        "3. Получаете рекомендации и фото продуктов\n"
        "4. Видите цены под каждым фото\n\n"
        "<b>Навигация:</b>\n"
        "↩️ <b>Назад</b> — вернуться на предыдущий шаг\n"
        "🏠 <b>В главное меню</b> — вернуться в начало\n\n"
        "<b>Команды:</b>\n"
        "/start - Перезапустить бота\n"
        "/help - Показать эту справку\n"
        "/status - Статус системы\n"
        "/contacts - Контакты салона"
    )

    await message.answer(
        help_text,
        reply_markup=keyboards.help_keyboard()
    )

@dp.message(Command("status"))
async def cmd_status(message: Message):
    try:
        stats = photo_map.get_photo_stats()

        status_text = (
            "📊 <b>Статус системы</b>\n\n"
            f"🤖 <b>Бот:</b> Активен ✅\n\n"
            f"📸 <b>Фотографии:</b>\n"
            f"• Всего продуктов: {stats['total']}\n"
            f"• Загружено фото: {stats['loaded']}\n"
            f"• Отсутствует: {stats['missing']}\n"
            f"• Прогресс: {stats['percentage']}%\n\n"
            f"🕐 <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}\n\n"
        )

        if stats['percentage'] < 50:
            status_text += "⚠️ <i>Рекомендуется загрузить фото продуктов через админ-панель</i>"
        else:
            status_text += "✅ <i>Система готова к работе</i>"

        await message.answer(
            status_text,
            reply_markup=keyboards.main_menu_keyboard()
        )

    except Exception as e:
        logger.error(f"❌ Ошибка в cmd_status: {e}")
        await message.answer("❌ Ошибка при получении статуса")

@dp.message(Command("contacts"))
async def cmd_contacts(message: Message):
    contacts_text = (
        "📞 <b>Контакты SVOY AV.COSMETIC</b>\n\n"
        f"{config.SALES_POINTS}\n\n"
        f"{config.DELIVERY_INFO}\n\n"
        "<b>💬 Связь с менеджером:</b>\n"
        "@SVOY_AVCOSMETIC"
    )

    await message.answer(
        contacts_text,
        reply_markup=keyboards.contacts_keyboard()
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    # Любой пользователь может попытаться войти в админку, проверка будет по паролю
    await state.set_state(AdminState.WAITING_PASSWORD)
    await message.answer(
        "🔐 <b>Доступ к админ-панели</b>\n\nВведите пароль для входа:",
        reply_markup=keyboards.back_to_menu_keyboard()
    )

# ==================== ВЫХОД ИЗ АДМИНКИ ====================

@dp.message(AdminState.ADMIN_MAIN_MENU, F.text == "🏠 В главное меню")
async def process_admin_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    
    await message.answer(
        "👋 <b>Добро пожаловать в SVOY AV.COSMETIC!</b>\n\n<i>Выберите категорию:</i>",
        reply_markup=keyboards.main_menu_keyboard()
    )
    await state.set_state(UserState.CHOOSING_CATEGORY)

@dp.message(AdminState.ADMIN_PHOTOS_MENU, F.text == "🏠 В главное меню")
async def process_admin_photos_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    
    await message.answer(
        "👋 <b>Добро пожаловать в SVOY AV.COSMETIC!</b>\n\n<i>Выберите категорию:</i>",
        reply_markup=keyboards.main_menu_keyboard()
    )
    await state.set_state(UserState.CHOOSING_CATEGORY)

@dp.message(AdminState.ADMIN_BULK_UPLOAD, F.text == "🏠 В главное меню")
async def process_admin_bulk_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    
    await message.answer(
        "👋 <b>Добро пожаловать в SVOY AV.COSMETIC!</b>\n\n<i>Выберите категорию:</i>",
        reply_markup=keyboards.main_menu_keyboard()
    )
    await state.set_state(UserState.CHOOSING_CATEGORY)
    
# ==================== НАВИГАЦИОННЫЕ КНОПКИ ====================

@dp.message(F.text == "❓ Помощь")
async def process_help(message: Message):
    await cmd_help(message)

@dp.message(F.text == "📞 Контакты")
async def process_contacts(message: Message):
    await cmd_contacts(message)

@dp.message(F.text == "📍 Точки продаж")
async def process_sales_points(message: Message):
    await message.answer(
        config.SALES_POINTS,
        reply_markup=keyboards.contacts_keyboard()
    )

@dp.message(F.text == "🚚 Доставка")
async def process_delivery(message: Message):
    await message.answer(
        config.DELIVERY_INFO,
        reply_markup=keyboards.contacts_keyboard()
    )

@dp.message(F.text == "💬 Написать менеджеру")
async def process_manager(message: Message):
    await message.answer(
        "💬 <b>Связь с менеджером</b>\n\n"
        "Для консультации и заказов напишите нашему менеджеру:\n"
        "@SVOY_AVCOSMETIC\n\n"
        "<i>Мы ответим в ближайшее время!</i>",
        reply_markup=keyboards.contacts_keyboard()
    )

@dp.message(F.text == "🏠 В главное меню")
async def process_main_menu(message: Message, state: FSMContext):
    await state.clear()
    clear_selected_problems(message.from_user.id)

    welcome_text = "👋 <b>Добро пожаловать в SVOY AV.COSMETIC!</b>\n\n<i>Выберите категорию:</i>"
    await message.answer(
        welcome_text,
        reply_markup=keyboards.main_menu_keyboard()
    )
    await state.set_state(UserState.CHOOSING_CATEGORY)

@dp.message(F.text == "↩️ Назад")
async def process_back(message: Message, state: FSMContext):
    """Обработчик кнопки 'Назад' - логический возврат на предыдущий шаг"""
    current_state = await state.get_state()

    # Определяем, на какой шаг вернуться
    if current_state == UserState.HAIR_CHOOSING_COLOR:
        await state.set_state(UserState.HAIR_CHOOSING_VOLUME)
        await message.answer(
            "<i>Хотите добавить объем волосам?</i>",
            reply_markup=keyboards.hair_volume_keyboard()
        )
    elif current_state == UserState.HAIR_CHOOSING_VOLUME:
        await state.set_state(UserState.HAIR_CHOOSING_SCALP)
        await message.answer(
            "<i>Чувствительная кожа головы?</i>",
            reply_markup=keyboards.scalp_type_keyboard()
        )
    elif current_state == UserState.HAIR_CHOOSING_SCALP:
        await state.set_state(UserState.HAIR_CHOOSING_PROBLEMS)
        selected_problems = get_selected_problems(message.from_user.id)
        await message.answer(
            "<i>Выберите проблемы волос (можно несколько):</i>\n"
            "<b>Нажмите на проблему, чтобы выбрать/отменить</b>\n\n"
            "<i>Можно нажать '✅ Готово' без выбора проблем</i>",
            reply_markup=keyboards.hair_problems_keyboard(selected_problems)
        )
    elif current_state == UserState.HAIR_CHOOSING_PROBLEMS:
        await state.set_state(UserState.HAIR_CHOOSING_TYPE)
        await message.answer(
            "💇‍♀️ <b>Отлично! Подберем уход для волос.</b>\n\n<i>Какой у вас тип волос?</i>",
            reply_markup=keyboards.hair_type_keyboard()
        )
    elif current_state == UserState.HAIR_CHOOSING_TYPE:
        await state.set_state(UserState.CHOOSING_CATEGORY)
        await message.answer(
            "👋 <b>Подберем идеальную косметику!</b>\n\n<i>Выберите категорию:</i>",
            reply_markup=keyboards.main_menu_keyboard()
        )
    elif current_state == UserState.BODY_CHOOSING_GOAL:
        await state.set_state(UserState.CHOOSING_CATEGORY)
        await message.answer(
            "👋 <b>Подберем идеальную косметику!</b>\n\n<i>Выберите категорию:</i>",
            reply_markup=keyboards.main_menu_keyboard()
        )
    else:
        await state.set_state(UserState.CHOOSING_CATEGORY)
        await message.answer(
            "👋 <b>Подберем идеальную косметику!</b>\n\n<i>Выберите категорию:</i>",
            reply_markup=keyboards.main_menu_keyboard()
        )

@dp.message(F.text == "💇‍♀️ Новая подборка волос")
async def process_new_hair_selection(message: Message, state: FSMContext):
    await state.clear()
    clear_selected_problems(message.from_user.id)
    await state.set_state(UserState.HAIR_CHOOSING_TYPE)

    await message.answer(
        "💇‍♀️ <b>Отлично! Подберем уход для волос.</b>\n\n<i>Какой у вас тип волос?</i>",
        reply_markup=keyboards.hair_type_keyboard()
    )

@dp.message(F.text == "🧴 Новая подборка тела")
async def process_new_body_selection(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(UserState.BODY_CHOOSING_GOAL)

    await message.answer(
        "🧴 <b>Прекрасно! Займемся уходом за телом.</b>\n\n<i>Какова ваша основная цель ухода?</i>",
        reply_markup=keyboards.body_goals_keyboard()
    )

# ==================== ОСНОВНАЯ ЛОГИКА БОТА ====================

@dp.message(UserState.CHOOSING_CATEGORY, F.text == "💇‍♀️ Волосы")
async def process_hair_category(message: Message, state: FSMContext):
    clear_selected_problems(message.from_user.id)
    await state.set_state(UserState.HAIR_CHOOSING_TYPE)
    await message.answer(
        "💇‍♀️ <b>Отлично! Подберем уход для волос.</b>\n\n<i>Какой у вас тип волос?</i>",
        reply_markup=keyboards.hair_type_keyboard()
    )

@dp.message(UserState.CHOOSING_CATEGORY, F.text == "🧴 Тело")
async def process_body_category(message: Message, state: FSMContext):
    await state.set_state(UserState.BODY_CHOOSING_GOAL)
    await message.answer(
        "🧴 <b>Прекрасно! Займемся уходом за телом.</b>\n\n<i>Какова ваша основная цель ухода?</i>",
        reply_markup=keyboards.body_goals_keyboard()
    )

# ==================== ОПРОС ДЛЯ ТЕЛА ====================

@dp.message(UserState.BODY_CHOOSING_GOAL, F.text.in_(config.BODY_GOALS))
async def process_body_goal(message: Message, state: FSMContext):
    try:
        goal = message.text
        save_user_data(message.from_user.id, "body_goal", goal)

        recommendations, photo_keys = await get_body_recommendations_with_photos(goal)

        # Отправляем рекомендации
        await message.answer(
            recommendations,
            reply_markup=keyboards.selection_complete_keyboard()
        )

        # Отправляем фото с ценами
        if photo_keys:
            await send_recommended_photos(
                message.chat.id,
                photo_keys,
                "🛍️ <b>Рекомендуемые продукты:</b>"
            )
        else:
            await message.answer(
                "📷 Фото продуктов для этой категории пока не загружены.",
                reply_markup=keyboards.selection_complete_keyboard()
            )

        # Отправляем контактную информацию
        await message.answer(
            config.SALES_POINTS + "\n\n" + config.DELIVERY_INFO,
            reply_markup=keyboards.selection_complete_keyboard()
        )

        await state.clear()
        logger.info(f"✅ Пользователь {message.from_user.id} получил рекомендации для тела: {goal}")

    except Exception as e:
        logger.error(f"❌ Ошибка в process_body_goal: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=keyboards.selection_complete_keyboard()
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
        "<b>Нажмите на проблему, чтобы выбрать/отменить</b>\n\n"
        "<i>Можно нажать '✅ Готово' без выбора проблем</i>",
        reply_markup=keyboards.hair_problems_keyboard([])
    )

@dp.message(UserState.HAIR_CHOOSING_PROBLEMS)
async def process_hair_problems(message: Message, state: FSMContext):
    if message.text == "✅ Готово":
        selected_problems = get_selected_problems(message.from_user.id)
        logger.info(f"Выбрано проблем: {selected_problems}")

        await state.set_state(UserState.HAIR_CHOOSING_SCALP)
        await message.answer(
            "<i>Чувствительная кожа головы?</i>",
            reply_markup=keyboards.scalp_type_keyboard()
        )

    elif message.text.startswith("☐ ") or message.text.startswith("✅ "):
        problem = message.text.replace("✅ ", "").replace("☐ ", "")

        if problem not in config.HAIR_PROBLEMS:
            return

        current_problems = get_selected_problems(message.from_user.id)

        if problem in current_problems:
            remove_selected_problem(message.from_user.id, problem)
        else:
            add_selected_problem(message.from_user.id, problem)

        await message.answer(
            "<i>Выберите проблемы волос (можно несколько):</i>\n"
            "<b>Нажмите на проблему, чтобы выбрать/отменить</b>\n\n"
            "<i>Можно нажать '✅ Готово' без выбора проблем</i>",
            reply_markup=keyboards.hair_problems_keyboard(get_selected_problems(message.from_user.id))
        )

@dp.message(UserState.HAIR_CHOOSING_SCALP, F.text.in_(config.SCALP_TYPES))
async def process_scalp_type(message: Message, state: FSMContext):
    scalp_type = message.text
    save_user_data(message.from_user.id, "scalp_type", scalp_type)

    await state.set_state(UserState.HAIR_CHOOSING_VOLUME)
    await message.answer(
        "<i>Хотите добавить объем волосам?</i>",
        reply_markup=keyboards.hair_volume_keyboard()
    )

@dp.message(UserState.HAIR_CHOOSING_VOLUME, F.text.in_(config.HAIR_VOLUME))
async def process_hair_volume(message: Message, state: FSMContext):
    hair_volume = message.text
    save_user_data(message.from_user.id, "hair_volume", hair_volume)

    hair_type = get_user_data_value(message.from_user.id, "hair_type", "")

    # Только для обычных "Окрашенных" показываем выбор цвета
    if hair_type == "Окрашенные":
        await state.set_state(UserState.HAIR_CHOOSING_COLOR)
        await message.answer(
            "<i>Выберите цвет волос:</i>",
            reply_markup=keyboards.hair_color_keyboard(hair_type)
        )
    else:
        # Для блондинок и натуральных сразу показываем результаты
        await show_hair_results(message, state)

@dp.message(UserState.HAIR_CHOOSING_COLOR, F.text.in_(["Брюнетка", "Шатенка", "Русая", "Рыжая"]))
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

        recommendations, photo_keys = await get_hair_recommendations_with_photos(
            hair_type, problems, scalp_type, hair_volume, hair_color
        )

        # Отправляем рекомендации
        await message.answer(
            recommendations,
            reply_markup=keyboards.selection_complete_keyboard()
        )

        # Отправляем фото с ценами
        if photo_keys:
            await send_recommended_photos(
                message.chat.id,
                photo_keys,
                "🛍️ <b>Рекомендуемые продукты:</b>"
            )
        else:
            await message.answer(
                "📷 Фото продуктов для этих рекомендаций пока не загружены.",
                reply_markup=keyboards.selection_complete_keyboard()
            )

        # Отправляем контактную информацию
        await message.answer(
            config.SALES_POINTS + "\n\n" + config.DELIVERY_INFO,
            reply_markup=keyboards.selection_complete_keyboard()
        )

        await state.clear()
        clear_selected_problems(message.from_user.id)
        logger.info(f"✅ Пользователь {message.from_user.id} получил рекомендации для волос")

    except Exception as e:
        logger.error(f"❌ Ошибка в show_hair_results: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при формировании рекомендаций. Попробуйте позже.",
            reply_markup=keyboards.selection_complete_keyboard()
        )
        await state.clear()

# ==================== АДМИН-ПАНЕЛЬ ====================

@dp.message(AdminState.WAITING_PASSWORD)
async def process_admin_password(message: Message, state: FSMContext):
    if message.text == config.ADMIN_PASSWORD:
        await state.set_state(AdminState.ADMIN_MAIN_MENU)
        await message.answer(
            "✅ <b>Доступ разрешен!</b>\n\nДобро пожаловать в админ-панель.",
            reply_markup=keyboards.admin_main_keyboard()
        )
        logger.info(f"🔐 Пользователь {message.from_user.id} вошел в админ-панель")
    else:
        await message.answer("❌ Неверный пароль. Попробуйте еще раз.")

# Главное меню админки
@dp.message(AdminState.ADMIN_MAIN_MENU, F.text == "📸 Управление фото")
async def process_admin_photos_menu(message: Message, state: FSMContext):
    await state.set_state(AdminState.ADMIN_PHOTOS_MENU)

    stats = photo_map.get_photo_stats()
    stats_text = format_photo_stats()

    await message.answer(
        f"📸 <b>Управление фотографиями</b>\n\n{stats_text}\n\n"
        "Выберите действие:",
        reply_markup=keyboards.admin_photos_keyboard()
    )

@dp.message(AdminState.ADMIN_MAIN_MENU, F.text == "📊 Статистика")
async def process_admin_stats(message: Message):
    stats = photo_map.get_photo_stats()
    stats_text = format_photo_stats()

    await message.answer(
        stats_text,
        reply_markup=keyboards.admin_main_keyboard()
    )

@dp.message(AdminState.ADMIN_MAIN_MENU, F.text == "🔄 Обновить список")
async def process_admin_refresh(message: Message):
    # Просто показываем обновленную статистику
    stats = photo_map.get_photo_stats()
    stats_text = format_photo_stats()

    await message.answer(
        f"🔄 <b>Список обновлен</b>\n\n{stats_text}",
        reply_markup=keyboards.admin_main_keyboard()
    )

# Меню управления фото
@dp.message(AdminState.ADMIN_PHOTOS_MENU, F.text == "📋 Список всех фото")
async def process_admin_photos_list(message: Message):
    missing_photos = photo_map.get_missing_photos()
    page = 0
    filter_type = "all"

    await message.answer(
        format_photo_list(missing_photos, page, filter_type),
        reply_markup=keyboards.admin_photos_list_keyboard(page, filter_type),
        parse_mode=ParseMode.HTML
    )

@dp.message(AdminState.ADMIN_PHOTOS_MENU, F.text == "📥 Массовая загрузка")
async def process_admin_bulk_upload(message: Message, state: FSMContext):
    await state.set_state(AdminState.ADMIN_BULK_UPLOAD)

    stats = photo_map.get_photo_stats()

    await message.answer(
        f"📥 <b>Массовая загрузка фото</b>\n\n"
        f"✅ <b>Загружено:</b> {stats['loaded']} из {stats['total']}\n"
        f"📈 <b>Прогресс:</b> {stats['percentage']}%\n\n"
        f"<b>Как это работает:</b>\n"
        f"1. Выберите категорию (Волосы/Тело)\n"
        f"2. Выберите подкатегорию\n"
        f"3. Отправляйте фото по одному\n"
        f"4. file_id автоматически сохранятся\n\n"
        f"Выберите категорию для загрузки:",
        reply_markup=keyboards.admin_bulk_upload_keyboard()
    )

@dp.message(AdminState.ADMIN_PHOTOS_MENU, F.text == "❌ Удалить все фото")
async def process_admin_reset_photos(message: Message, state: FSMContext):
    await state.set_state(AdminState.ADMIN_CONFIRM_RESET)

    stats = photo_map.get_photo_stats()

    await message.answer(
        f"⚠️ <b>ВНИМАНИЕ!</b>\n\n"
        f"Вы собираетесь удалить ВСЕ загруженные фото.\n\n"
        f"📊 <b>Текущая статистика:</b>\n"
        f"• Загружено фото: {stats['loaded']}\n"
        f"• Всего продуктов: {stats['total']}\n\n"
        f"<b>Это действие нельзя отменить!</b>\n\n"
        f"Вы уверены, что хотите удалить все фото?",
        reply_markup=keyboards.admin_confirm_reset_keyboard()
    )

@dp.message(AdminState.ADMIN_PHOTOS_MENU, F.text == "↩️ Назад в админку")
async def process_admin_back_to_main(message: Message, state: FSMContext):
    await state.set_state(AdminState.ADMIN_MAIN_MENU)
    await message.answer(
        "Главное меню админки:",
        reply_markup=keyboards.admin_main_keyboard()
    )

# Массовая загрузка
@dp.message(AdminState.ADMIN_BULK_UPLOAD, F.text == "💇‍♀️ Загрузить ВОЛОСЫ")
async def process_bulk_hair(message: Message):
    await message.answer(
        "💇‍♀️ <b>Загрузка фото для ВОЛОС</b>\n\n"
        "Выберите подкатегорию:",
        reply_markup=keyboards.admin_category_bulk_keyboard()
    )

@dp.message(AdminState.ADMIN_BULK_UPLOAD, F.text == "🧴 Загрузить ТЕЛО")
async def process_bulk_body(message: Message):
    await message.answer(
        "🧴 <b>Загрузка фото для ТЕЛА</b>\n\n"
        "Выберите подкатегорию:",
        reply_markup=keyboards.admin_category_bulk_keyboard()
    )

@dp.message(AdminState.ADMIN_BULK_UPLOAD, F.text == "📋 Показать прогресс")
async def process_bulk_progress(message: Message):
    stats = photo_map.get_photo_stats()
    stats_text = format_photo_stats()

    await message.answer(
        f"📋 <b>Прогресс загрузки</b>\n\n{stats_text}",
        reply_markup=keyboards.admin_bulk_upload_keyboard()
    )

@dp.message(AdminState.ADMIN_BULK_UPLOAD, F.text == "↩️ Назад к фото")
async def process_bulk_back_to_photos(message: Message, state: FSMContext):
    await state.set_state(AdminState.ADMIN_PHOTOS_MENU)

    stats = photo_map.get_photo_stats()
    stats_text = format_photo_stats()

    await message.answer(
        f"📸 <b>Управление фотографиями</b>\n\n{stats_text}\n\n"
        "Выберите действие:",
        reply_markup=keyboards.admin_photos_keyboard()
    )

# ==================== CALLBACK QUERIES ДЛЯ АДМИНКИ ====================

@dp.callback_query(F.data.startswith("bulk_category:"))
async def process_bulk_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]  # "волосы" или "тело"

    category_name = "💇‍♀️ Волосы" if category == "волосы" else "🧴 Тело"

    await callback.message.edit_text(
        f"{category_name} - <b>Выберите подкатегорию:</b>",
        reply_markup=keyboards.admin_subcategory_bulk_keyboard(category),
        parse_mode=ParseMode.HTML
    )

    await callback.answer()

@dp.callback_query(F.data == "bulk_back_to_categories")
async def process_bulk_back_to_categories(callback: CallbackQuery):
    await callback.message.edit_text(
        "📥 <b>Массовая загрузка фото</b>\n\n"
        "Выберите категорию для загрузки:",
        reply_markup=keyboards.admin_category_bulk_keyboard(),
        parse_mode=ParseMode.HTML
    )

    await callback.answer()

@dp.callback_query(F.data.startswith("bulk_subcategory_idx:"))
async def process_bulk_subcategory(callback: CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split(":")
        category = parts[1]  # "волосы" или "тело"
        idx = int(parts[2])  # индекс подкатегории
        
        category_name = "💇‍♀️ Волосы" if category == "волосы" else "🧴 Тело"
        subcategories = list(config.PHOTO_STRUCTURE_ADMIN[category_name].items())
        
        if idx >= len(subcategories):
            await callback.answer("❌ Ошибка индекса")
            return
        
        subcategory_name, products = subcategories[idx]
        
        # Сохраняем текущую подкатегорию в состоянии
        await state.update_data(
            bulk_category=category,
            bulk_subcategory=subcategory_name,
            bulk_products=products,
            bulk_current_index=0
        )
        
        await state.set_state(AdminState.ADMIN_WAITING_BULK_PHOTO)
        
        # Показываем первый продукт для загрузки
        product_key, product_name = products[0]
        current_file_id = photo_map.get_photo_file_id(product_key)
        
        text = (
            f"📥 <b>Массовая загрузка</b>\n\n"
            f"<b>Категория:</b> {category_name}\n"
            f"<b>Подкатегория:</b> {subcategory_name}\n\n"
            f"<b>Текущий продукт (1/{len(products)}):</b>\n"
            f"• {product_name}\n"
            f"• Ключ: <code>{product_key}</code>\n\n"
        )
        
        if current_file_id:
            text += f"✅ <i>Уже загружено</i>\n"
            text += f"• file_id: <code>{current_file_id[:30]}...</code>\n\n"
            text += f"<i>Отправьте новое фото для замены или нажмите 'Пропустить'</i>"
        else:
            text += f"❌ <i>Еще не загружено</i>\n\n"
            text += f"<i>Отправьте фото этого продукта</i>"
        
        # Создаем inline-клавиатуру
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(
                text="⏭️ Пропустить",
                callback_data=f"bulk_skip:{product_key}"
            ),
            types.InlineKeyboardButton(
                text="🛑 Остановить",
                callback_data="bulk_stop"
            )
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.HTML
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Ошибка в process_bulk_subcategory: {e}")
        await callback.answer("❌ Произошла ошибка")

@dp.callback_query(F.data.startswith("bulk_skip:"))
async def process_bulk_skip(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    products = data.get("bulk_products", [])
    current_index = data.get("bulk_current_index", 0)

    # Переходим к следующему продукту
    current_index += 1

    if current_index >= len(products):
        # Все продукты обработаны
        category_name = "💇‍♀️ Волосы" if data.get("bulk_category") == "волосы" else "🧴 Тело"
        subcategory_name = data.get("bulk_subcategory", "")

        await callback.message.edit_text(
            f"✅ <b>Загрузка завершена!</b>\n\n"
            f"<b>Категория:</b> {category_name}\n"
            f"<b>Подкатегория:</b> {subcategory_name}\n"
            f"<b>Обработано продуктов:</b> {len(products)}\n\n"
            f"Вы можете продолжить загрузку в другой подкатегории.",
            reply_markup=keyboards.admin_category_bulk_keyboard(),
            parse_mode=ParseMode.HTML
        )

        await state.set_state(AdminState.ADMIN_BULK_UPLOAD)
        await callback.answer("✅ Все продукты обработаны!")
        return

    # Показываем следующий продукт
    await state.update_data(bulk_current_index=current_index)

    product_key, product_name = products[current_index]
    current_file_id = photo_map.get_photo_file_id(product_key)

    text = (
        f"📥 <b>Массовая загрузка</b>\n\n"
        f"<b>Категория:</b> {'💇‍♀️ Волосы' if data.get('bulk_category') == 'волосы' else '🧴 Тело'}\n"
        f"<b>Подкатегория:</b> {data.get('bulk_subcategory', '')}\n\n"
        f"<b>Текущий продукт ({current_index + 1}/{len(products)}):</b>\n"
        f"• {product_name}\n"
        f"• Ключ: <code>{product_key}</code>\n\n"
    )

    if current_file_id:
        text += f"✅ <i>Уже загружено</i>\n"
        text += f"• file_id: <code>{current_file_id[:30]}...</code>\n\n"
        text += f"<i>Отправьте новое фото для замены или нажмите 'Пропустить'</i>"
    else:
        text += f"❌ <i>Еще не загружено</i>\n\n"
        text += f"<i>Отправьте фото этого продукта</i>"

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="⏭️ Пропустить",
            callback_data=f"bulk_skip:{product_key}"
        ),
        types.InlineKeyboardButton(
            text="🛑 Остановить",
            callback_data="bulk_stop"
        )
    )

    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

    await callback.answer("⏭️ Пропущено")

@dp.callback_query(F.data == "bulk_stop")
async def process_bulk_stop(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_index = data.get("bulk_current_index", 0)

    await callback.message.edit_text(
        f"🛑 <b>Загрузка остановлена</b>\n\n"
        f"<b>Обработано продуктов:</b> {current_index + 1}\n\n"
        f"Вы можете продолжить загрузку в другой подкатегории.",
        reply_markup=keyboards.admin_category_bulk_keyboard(),
        parse_mode=ParseMode.HTML
    )

    await state.set_state(AdminState.ADMIN_BULK_UPLOAD)
    await callback.answer("🛑 Загрузка остановлена")

# Обработка фото в режиме массовой загрузки
@dp.message(AdminState.ADMIN_WAITING_BULK_PHOTO, F.photo)
async def process_bulk_photo(message: Message, state: FSMContext):
    logger.info(f"📸 Получено фото в режиме массовой загрузки")
    
    data = await state.get_data()
    products = data.get("bulk_products", [])
    current_index = data.get("bulk_current_index", 0)

    if current_index >= len(products):
        await message.answer("❌ Ошибка: список продуктов пуст.")
        return

    product_key, product_name = products[current_index]
    photo = message.photo[-1]
    file_id = photo.file_id

    # Сохраняем фото
    success = photo_map.set_photo_file_id(product_key, file_id)

    if success:
        # Переходим к следующему продукту
        current_index += 1

        if current_index >= len(products):
            # Все продукты обработаны
            category_name = "💇‍♀️ Волосы" if data.get("bulk_category") == "волосы" else "🧴 Тело"
            subcategory_name = data.get("bulk_subcategory", "")

            # Показываем полный file_id
            await message.answer(
                f"✅ <b>Фото сохранено!</b>\n\n"
                f"<b>Продукт:</b> {product_name}\n"
                f"<b>Ключ:</b> <code>{product_key}</code>\n"
                f"<b>file_id:</b> <code>{file_id}</code>\n\n"
                f"📥 <b>Загрузка завершена!</b>\n\n"
                f"<b>Категория:</b> {category_name}\n"
                f"<b>Подкатегория:</b> {subcategory_name}\n"
                f"<b>Обработано продуктов:</b> {len(products)}\n\n"
                f"Вы можете продолжить загрузку в другой подкатегории.",
                reply_markup=keyboards.admin_category_bulk_keyboard()
            )

            await state.set_state(AdminState.ADMIN_BULK_UPLOAD)
            return

        # Показываем следующий продукт
        await state.update_data(bulk_current_index=current_index)

        next_product_key, next_product_name = products[current_index]
        next_file_id = photo_map.get_photo_file_id(next_product_key)

        text = (
            f"✅ <b>Фото сохранено!</b>\n\n"
            f"<b>Продукт:</b> {product_name}\n"
            f"<b>Ключ:</b> <code>{product_key}</code>\n"
            f"<b>file_id:</b> <code>{file_id}</code>\n\n"
            f"📥 <b>Следующий продукт ({current_index + 1}/{len(products)}):</b>\n"
            f"• {next_product_name}\n"
            f"• Ключ: <code>{next_product_key}</code>\n\n"
        )

        if next_file_id:
            text += f"✅ <i>Уже загружено</i>\n"
            text += f"• file_id: <code>{next_file_id[:30]}...</code>\n\n"
            text += f"<i>Отправьте новое фото для замены или нажмите 'Пропустить'</i>"
        else:
            text += f"❌ <i>Еще не загружено</i>\n\n"
            text += f"<i>Отправьте фото этого продукта</i>"

        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(
                text="⏭️ Пропустить",
                callback_data=f"bulk_skip:{next_product_key}"
            ),
            types.InlineKeyboardButton(
                text="🛑 Остановить",
                callback_data="bulk_stop"
            )
        )

        await message.answer(
            text,
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer(
            f"❌ <b>Ошибка сохранения!</b>\n\n"
            f"Не удалось сохранить фото для продукта: {product_name}\n"
            f"Ключ: <code>{product_key}</code>",
            parse_mode=ParseMode.HTML
        )

# Fallback обработчик для текста в режиме массовой загрузки
@dp.message(AdminState.ADMIN_WAITING_BULK_PHOTO)
async def handle_bulk_state_text(message: Message, state: FSMContext):
    data = await state.get_data()
    products = data.get("bulk_products", [])
    current_index = data.get("bulk_current_index", 0)
    
    if current_index < len(products):
        product_key, product_name = products[current_index]
        
        await message.answer(
            f"📸 <b>Вы в режиме загрузки фото!</b>\n\n"
            f"<b>Текущий продукт:</b> {product_name}\n"
            f"<b>Ключ:</b> <code>{product_key}</code>\n\n"
            f"<i>Просто отправьте фото этого продукта или используйте кнопки.</i>",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer(
            f"📸 <b>Режим загрузки фото</b>\n\n"
            f"<i>Просто отправьте фото продукта.</i>",
            parse_mode=ParseMode.HTML
        )

# Обработка callback для списка фото
@dp.callback_query(F.data.startswith("photos_list:"))
async def process_photos_list(callback: CallbackQuery):
    parts = callback.data.split(":")
    filter_type = parts[1]
    page = int(parts[2])

    missing_photos = photo_map.get_missing_photos()

    await callback.message.edit_text(
        format_photo_list(missing_photos, page, filter_type),
        reply_markup=keyboards.admin_photos_list_keyboard(page, filter_type),
        parse_mode=ParseMode.HTML
    )

    await callback.answer()

@dp.callback_query(F.data == "bulk_upload_start")
async def process_bulk_upload_start(callback: CallbackQuery):
    await callback.message.edit_text(
        "📥 <b>Массовая загрузка фото</b>\n\n"
        "Выберите категорию для загрузки:",
        reply_markup=keyboards.admin_category_bulk_keyboard(),
        parse_mode=ParseMode.HTML
    )

    await callback.answer()

@dp.callback_query(F.data == "admin_back_to_main")
async def process_admin_back_to_main_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.ADMIN_MAIN_MENU)

    await callback.message.edit_text(
        "Главное меню админки:",
        reply_markup=keyboards.admin_main_keyboard()
    )

    await callback.answer()

@dp.callback_query(F.data == "confirm_reset_photos")
async def process_confirm_reset(callback: CallbackQuery, state: FSMContext):
    success = photo_map.reset_all_photos()

    if success:
        await callback.message.edit_text(
            "✅ <b>Все фото успешно удалены!</b>\n\n"
            "База фотографий очищена. Теперь вы можете начать загрузку заново.",
            reply_markup=keyboards.admin_photos_keyboard(),
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.message.edit_text(
            "❌ <b>Ошибка при удалении фото!</b>\n\n"
            "Попробуйте еще раз или проверьте права доступа к файлу.",
            reply_markup=keyboards.admin_photos_keyboard(),
            parse_mode=ParseMode.HTML
        )

    await state.set_state(AdminState.ADMIN_PHOTOS_MENU)
    await callback.answer()

@dp.callback_query(F.data == "cancel_reset_photos")
async def process_cancel_reset(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.ADMIN_PHOTOS_MENU)

    stats = photo_map.get_photo_stats()
    stats_text = format_photo_stats()

    await callback.message.edit_text(
        f"📸 <b>Управление фотографиями</b>\n\n{stats_text}\n\n"
        "Удаление отменено. Выберите действие:",
        reply_markup=keyboards.admin_photos_keyboard(),
        parse_mode=ParseMode.HTML
    )

    await callback.answer("❌ Удаление отменено")

@dp.callback_query(F.data == "no_action")
async def process_no_action(callback: CallbackQuery):
    await callback.answer()

# ==================== ЗАПУСК БОТА ====================

async def main():
    """Основная функция запуска бота"""
    try:
        logger.info("🚀 Запуск бота с массовой загрузкой фото...")
        
        # Запускаем health check сервер
        start_health_server()
        logger.info("✅ Health check сервер запущен")
        
        # Показываем статистику фото
        stats = photo_map.get_photo_stats()
        logger.info(f"📸 Статистика фото: {stats['loaded']}/{stats['total']} ({stats['percentage']}%)")
        
        # Удаляем webhook для чистого запуска
        await bot.delete_webhook(drop_pending_updates=True)

        # ЗАПУСКАЕМ KEEP-ALIVE ЗАДАЧУ (чтобы бот не спал на Render Free)
        async def keep_alive():
            while True:
                try:
                    me = await bot.get_me()
                    logger.info(f"🤖 Keep-alive: Бот активен (@{me.username}) - {stats['loaded']}/{stats['total']} фото")
                except Exception as e:
                    logger.error(f"❌ Keep-alive ошибка: {e}")
                await asyncio.sleep(600)  # 10 минут
        
        # Запускаем в фоне
        asyncio.create_task(keep_alive())
        logger.info("✅ Keep-alive задача запущена (пинг каждые 10 минут)")
        
        # Запускаем поллинг
        logger.info("🔄 Запуск поллинга...")
        await dp.start_polling(bot)
        
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

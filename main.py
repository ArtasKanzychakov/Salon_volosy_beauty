"""
MAIN.PY - ФИНАЛЬНАЯ ВЕРСИЯ для Render со статическим хранилищем фото
"""

import os
import logging
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

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

# Инициализация бота
bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

async def send_recommended_photos(chat_id: int, photo_keys: list, caption: str = ""):
    """Отправка рекомендованных фото из статического хранилища"""
    try:
        if not photo_keys:
            await bot.send_message(
                chat_id, 
                "📷 Фото продуктов для этих рекомендаций пока не загружены.\n\n"
                "Администратор скоро добавит фотографии!",
                reply_markup=keyboards.selection_complete_keyboard()
            )
            return

        sent_count = 0
        for photo_key in photo_keys:
            file_id = photo_map.get_photo_file_id(photo_key)
            if file_id:
                # Находим отображаемое имя
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
                await asyncio.sleep(0.5)  # Небольшая задержка между фото

        if sent_count == 0:
            await bot.send_message(
                chat_id,
                "📷 Фото продуктов временно недоступны.\n\n"
                "Администратор еще не загрузил фотографии для этих продуктов.",
                reply_markup=keyboards.selection_complete_keyboard()
            )

    except Exception as e:
        logger.error(f"❌ Ошибка при отправке фото: {e}")
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
            chocolate_keys = config.PHOTO_MAPPING["волосы"].get("оттенечная_шоколад", [])
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
        "3. Получаете рекомендации и фото продуктов\n\n"
        "<b>Навигация:</b>\n"
        "↩️ <b>Назад</b> — вернуться на предыдущий шаг\n"
        "🏠 <b>В главное меню</b> — вернуться в начало"
    )

    await message.answer(
        help_text,
        reply_markup=keyboards.main_menu_keyboard()
    )

@dp.message(Command("status"))
async def cmd_status(message: Message):
    try:
        all_photos = photo_map.get_all_photos()
        photo_count = len(all_photos)
        
        hair_count = 0
        body_count = 0
        
        for key, file_id in all_photos.items():
            if file_id:  # Проверяем, что фото загружено
                if key in config.PHOTO_STRUCTURE.get("волосы", {}):
                    hair_count += 1
                elif key in config.PHOTO_STRUCTURE.get("тело", {}):
                    body_count += 1

        status_text = (
            "📊 <b>Статус системы</b>\n\n"
            f"🤖 <b>Бот:</b> Активен ✅\n\n"
            f"📈 <b>Статистика фото:</b>\n"
            f"• Всего загружено: {photo_count}\n"
            f"• Волосы: {hair_count}\n"
            f"• Тело: {body_count}\n\n"
            f"🕐 <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}"
        )

        await message.answer(
            status_text,
            reply_markup=keyboards.main_menu_keyboard()
        )

    except Exception as e:
        logger.error(f"❌ Ошибка в cmd_status: {e}")
        await message.answer("❌ Ошибка при получении статуса")

@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
        
    await state.set_state(AdminState.WAITING_PASSWORD)
    await message.answer(
        "🔐 <b>Доступ к админ-панели</b>\n\nВведите пароль для входа:",
        reply_markup=keyboards.back_to_menu_keyboard()
    )

# ==================== НАВИГАЦИОННЫЕ КНОПКИ ====================

@dp.message(F.text == "❓ Помощь")
async def process_help(message: Message):
    await cmd_help(message)

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

# ==================== ГЛАВНОЕ МЕНЮ И ВЫБОР КАТЕГОРИИ ====================

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

        await message.answer(
            recommendations,
            reply_markup=keyboards.selection_complete_keyboard()
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
                reply_markup=keyboards.selection_complete_keyboard()
            )

        await message.answer(
            config.SALES_POINTS + "\n\n" + config.DELIVERY_INFO,
            reply_markup=keyboards.selection_complete_keyboard()
        )

        await state.clear()
        logger.info(f"✅ Пользователь {message.from_user.id} получил рекомендации для тела: {goal}")

    except Exception as e:
        logger.error(f"❌ Ошибка в process_body_goal: {e}")
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

    if hair_type == "Окрашенные":
        await state.set_state(UserState.HAIR_CHOOSING_COLOR)
        await message.answer(
            "<i>Выберите цвет волос:</i>",
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

        recommendations, photo_keys = await get_hair_recommendations_with_photos(
            hair_type, problems, scalp_type, hair_volume, hair_color
        )

        await message.answer(
            recommendations,
            reply_markup=keyboards.selection_complete_keyboard()
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
                reply_markup=keyboards.selection_complete_keyboard()
            )

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

# ==================== АДМИН-ПАНЕЛЬ (ТОЛЬКО ДЛЯ ПОЛУЧЕНИЯ FILE_ID) ====================

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

@dp.message(AdminState.ADMIN_MAIN_MENU, F.text == "📊 Проверить фото")
async def process_admin_check_photos(message: Message):
    try:
        all_photos = photo_map.get_all_photos()
        photo_count = len(all_photos)
        
        hair_count = 0
        body_count = 0
        
        for key, file_id in all_photos.items():
            if file_id:
                if key in config.PHOTO_STRUCTURE.get("волосы", {}):
                    hair_count += 1
                elif key in config.PHOTO_STRUCTURE.get("тело", {}):
                    body_count += 1

        stats_text = "📊 <b>Статистика фото</b>\n\n"
        stats_text += f"• Всего загружено: {photo_count}\n"
        stats_text += f"• Волосы: {hair_count}\n"
        stats_text += f"• Тело: {body_count}\n\n"
        
        if photo_count < 5:
            stats_text += "⚠️ <b>Внимание:</b> Загружено мало фото. Рекомендуется загрузить основные продукты."
        
        await message.answer(
            stats_text,
            reply_markup=keyboards.admin_main_keyboard()
        )

    except Exception as e:
        logger.error(f"❌ Ошибка при проверке фото: {e}")
        await message.answer("❌ Ошибка при проверке фото.")

@dp.message(AdminState.ADMIN_MAIN_MENU, F.text == "📸 Получить file_id")
async def process_admin_get_file_id(message: Message, state: FSMContext):
    await state.set_state(AdminState.ADMIN_CHOOSING_SUBCATEGORY)
    await message.answer(
        "📸 <b>Получение file_id фото</b>\n\nВыберите категорию:",
        reply_markup=keyboards.admin_category_keyboard()
    )

@dp.message(AdminState.ADMIN_CHOOSING_SUBCATEGORY, F.text.in_(["💇‍♀️ Волосы", "🧴 Тело"]))
async def process_admin_category(message: Message, state: FSMContext):
    category = "волосы" if message.text == "💇‍♀️ Волосы" else "тело"
    await state.update_data(admin_category=category)
    
    await message.answer(
        f"Выберите подкатегорию для <b>{category}</b>:",
        reply_markup=keyboards.admin_subcategory_keyboard(category)
    )

@dp.message(AdminState.ADMIN_CHOOSING_SUBCATEGORY, F.text != "↩️ Назад")
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
        reply_markup=keyboards.admin_products_keyboard(category, subcategory)
    )

@dp.message(AdminState.ADMIN_CHOOSING_SUBCATEGORY, F.text == "↩️ Назад")
async def process_admin_back_to_categories(message: Message, state: FSMContext):
    await state.set_state(AdminState.ADMIN_MAIN_MENU)
    await message.answer(
        "Главное меню админки:",
        reply_markup=keyboards.admin_main_keyboard()
    )

@dp.message(AdminState.ADMIN_CHOOSING_PRODUCT_NAME, F.text != "↩️ Назад")
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

    await state.update_data(admin_product_key=product_key)
    await state.set_state(AdminState.ADMIN_WAITING_PHOTO)
    
    current_file_id = photo_map.get_photo_file_id(product_key)
    status = "✅ Уже есть" if current_file_id else "❌ Нет фото"
    
    await message.answer(
        f"📸 <b>Отправьте фото для продукта:</b>\n\n"
        f"<b>Продукт:</b> {product_display_name}\n"
        f"<b>Ключ:</b> <code>{product_key}</code>\n"
        f"<b>Статус:</b> {status}\n\n"
        f"<i>После отправки фото вы получите его file_id.</i>\n"
        f"<i>Скопируйте file_id и вставьте в файл photo_map.py</i>",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(AdminState.ADMIN_CHOOSING_PRODUCT_NAME, F.text == "↩️ Назад")
async def process_admin_back_to_subcategories(message: Message, state: FSMContext):
    data = await state.get_data()
    category = data.get("admin_category")
    await state.set_state(AdminState.ADMIN_CHOOSING_SUBCATEGORY)
    await message.answer(
        f"Выберите подкатегорию для <b>{category}</b>:",
        reply_markup=keyboards.admin_subcategory_keyboard(category)
    )

@dp.message(AdminState.ADMIN_WAITING_PHOTO, F.photo)
async def process_admin_photo(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        product_key = data.get("admin_product_key")
        
        if not product_key:
            await message.answer("❌ Ошибка: продукт не выбран.")
            await state.set_state(AdminState.ADMIN_MAIN_MENU)
            await message.answer(
                "Возврат в админ-меню.",
                reply_markup=keyboards.admin_main_keyboard()
            )
            return

        photo = message.photo[-1]
        file_id = photo.file_id

        # Находим отображаемое имя для продукта
        display_name = product_key
        for category in config.PHOTO_STRUCTURE.values():
            for subcat_products in category.values():
                for key, name in subcat_products:
                    if key == product_key:
                        display_name = name
                        break

        await message.answer(
            f"✅ <b>Фото получено!</b>\n\n"
            f"<b>Продукт:</b> {display_name}\n"
            f"<b>Ключ:</b> <code>{product_key}</code>\n\n"
            f"<b>file_id:</b>\n<code>{file_id}</code>\n\n"
            f"<i>Скопируйте file_id и вставьте в файл photo_map.py:</i>\n\n"
            f"<code>\"{product_key}\": \"{file_id}\",</code>\n\n"
            f"После этого перезапустите бота.",
            reply_markup=keyboards.admin_main_keyboard()
        )

        await state.set_state(AdminState.ADMIN_MAIN_MENU)
        logger.info(f"📸 Админ получил file_id для {product_key}: {file_id[:20]}...")

    except Exception as e:
        logger.error(f"❌ Ошибка при обработке фото админа: {e}", exc_info=True)
        await message.answer(
            f"❌ <b>Ошибка:</b>\n\n<code>{str(e)[:200]}</code>",
            reply_markup=keyboards.admin_main_keyboard()
        )
        await state.set_state(AdminState.ADMIN_MAIN_MENU)

# ==================== ЗАПУСК БОТА ====================

async def main():
    """Основная функция запуска бота"""
    try:
        logger.info("🚀 Запуск бота со статическим хранилищем фото...")
        
        # Удаляем webhook для чистого запуска
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Запускаем поллинг
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
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, InputFile
from aiogram.utils import executor

from config import BOT_TOKEN, WELCOME_TEXT, EMOJI, LOCATIONS_TEXT, DELIVERY_TEXT
from keyboards import (
    get_main_menu, get_back_menu, get_body_care_menu, 
    get_hair_type_menu, get_problems_inline_keyboard,
    get_yes_no_menu, get_volume_menu, get_hair_color_menu,
    get_final_menu
)
from database import storage
from recommendations import (
    BODY_CARE_RECOMMENDATIONS, HAIR_BASE_RECOMMENDATIONS,
    HAIR_PROBLEMS_RECOMMENDATIONS, VOLUME_RECOMMENDATION,
    SENSITIVE_SCALP_RECOMMENDATION, COLOR_MASKS,
    LOCATIONS, DELIVERY_TEXT as REC_DELIVERY_TEXT
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Состояния
class Form(StatesGroup):
    main = State()
    body = State()
    hair = State()
    hair_type = State()
    problems = State()
    scalp = State()
    volume = State()
    color = State()
    result = State()

# ========== РЕКОМЕНДАЦИИ (обновленные) ==========

BODY_RECOMMENDATIONS = {
    "Общий уход и увлажнение": BODY_CARE_RECOMMENDATIONS["general"],
    "Сухая кожа": BODY_CARE_RECOMMENDATIONS["dry"],
    "Чувствительная кожа": BODY_CARE_RECOMMENDATIONS["sensitive"],
    "Борьба с целлюлитом": BODY_CARE_RECOMMENDATIONS["cellulite"]
}

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

@dp.message_handler(commands=['start', 'restart'], state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик старта"""
    await state.finish()
    storage.delete(message.from_user.id)

    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu())
    await Form.main.set()

@dp.message_handler(text="🔄 Начать заново", state='*')
async def cmd_restart(message: types.Message, state: FSMContext):
    """Обработчик перезапуска"""
    await cmd_start(message, state)

@dp.message_handler(text="◀️ Назад", state='*')
async def cmd_back(message: types.Message, state: FSMContext):
    """Обработчик кнопки Назад"""
    current_state = await state.get_state()

    if current_state == Form.body.state:
        await message.answer("Главное меню:", reply_markup=get_main_menu())
        await Form.main.set()
    elif current_state in [Form.hair_type.state, Form.problems.state, Form.scalp.state, Form.volume.state, Form.color.state]:
        await message.answer("Главное меню:", reply_markup=get_main_menu())
        await Form.main.set()
    else:
        await cmd_start(message, state)

# ========== ГЛАВНОЕ МЕНЮ ==========

@dp.message_handler(text="🧴 Уход за телом", state=Form.main)
async def body_care_handler(message: types.Message):
    """Выбран уход за телом"""
    await message.answer("Выберите задачу для кожи тела:", reply_markup=get_body_care_menu())
    await Form.body.set()

@dp.message_handler(text="💇‍♀️ Уход за волосами", state=Form.main)
async def hair_care_handler(message: types.Message):
    """Выбран уход за волосами"""
    await message.answer("Ваши волосы окрашены?", reply_markup=get_hair_type_menu())
    await Form.hair_type.set()

# ========== УХОД ЗА ТЕЛОМ (с изображениями) ==========

@dp.message_handler(state=Form.body)
async def body_type_handler(message: types.Message, state: FSMContext):
    """Обработка выбора типа кожи тела"""
    text = message.text

    if text not in BODY_RECOMMENDATIONS:
        await message.answer("Пожалуйста, выберите вариант из списка:", reply_markup=get_body_care_menu())
        return

    recommendation = BODY_RECOMMENDATIONS[text]
    
    # Формируем ответ с изображением
    products_text = "\n".join(recommendation["products"])
    
    response = f"""
{recommendation['title']}

{products_text}

{LOCATIONS}

{REC_DELIVERY_TEXT}

🔄 *Для нового подбора нажмите «Начать заново»*
    """
    
    # Отправляем изображение с подписью
    try:
        await message.answer_photo(
            photo=recommendation["image"],
            caption=response,
            reply_markup=get_final_menu()
        )
    except Exception as e:
        # Если не удалось отправить фото, отправляем текст
        logger.error(f"Ошибка отправки фото: {e}")
        await message.answer(response, reply_markup=get_final_menu())
    
    await Form.result.set()

# ========== УХОД ЗА ВОЛОСАМИ (с изображениями) ==========

@dp.message_handler(state=Form.hair_type)
async def hair_type_handler(message: types.Message, state: FSMContext):
    """Обработка выбора типа волос"""
    text = message.text

    if "блондинка" in text.lower():
        hair_type = "blonde"
    elif "окрашенные" in text.lower():
        hair_type = "colored"
    elif "натуральные" in text.lower():
        hair_type = "natural"
    else:
        await message.answer("Пожалуйста, выберите вариант из списка:", reply_markup=get_hair_type_menu())
        return

    storage.save(message.from_user.id, "hair_type", hair_type)
    
    # Просим выбрать проблемы
    await message.answer("🔧 Выберите проблемы волос (можно несколько):", reply_markup=get_back_menu())
    await message.answer("Нажмите на проблему для выбора:", reply_markup=get_problems_inline_keyboard())
    await Form.problems.set()

@dp.callback_query_handler(lambda c: c.data.startswith('prob_'), state=Form.problems)
async def process_problem_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора проблемы"""
    problem_id = callback_query.data.replace('prob_', '')
    user_id = callback_query.from_user.id

    current_problems = storage.get(user_id, "problems") or []

    if problem_id == 'none':
        current_problems = ['none']
    elif problem_id in current_problems:
        current_problems.remove(problem_id)
        if 'none' in current_problems:
            current_problems.remove('none')
    else:
        if 'none' in current_problems:
            current_problems = []
        current_problems.append(problem_id)

    storage.save(user_id, "problems", current_problems)

    await bot.edit_message_reply_markup(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=get_problems_inline_keyboard(current_problems)
    )

    await bot.answer_callback_query(callback_query.id)

@dp.callback_query_handler(lambda c: c.data == 'done', state=Form.problems)
async def problems_done_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """Завершение выбора проблем"""
    user_id = callback_query.from_user.id
    problems = storage.get(user_id, "problems")

    if not problems:
        await bot.answer_callback_query(callback_query.id, "Выберите хотя бы одну проблему или 'Нет проблем'")
        return

    await bot.answer_callback_query(callback_query.id, "Выбор сохранён!")
    await bot.send_message(callback_query.message.chat.id, "Есть ли чувствительная кожа головы?", reply_markup=get_yes_no_menu())
    await Form.scalp.set()

@dp.message_handler(state=Form.scalp)
async def scalp_handler(message: types.Message, state: FSMContext):
    """Обработка выбора типа кожи головы"""
    if message.text not in ["Да", "Нет"]:
        await message.answer("Пожалуйста, ответьте Да или Нет:", reply_markup=get_yes_no_menu())
        return

    storage.save(message.from_user.id, "scalp", message.text == "Да")
    await message.answer("Нужен дополнительный объем?", reply_markup=get_volume_menu())
    await Form.volume.set()

@dp.message_handler(state=Form.volume)
async def volume_handler(message: types.Message, state: FSMContext):
    """Обработка выбора объема"""
    user_id = message.from_user.id

    if "хочу объем" in message.text.lower():
        storage.save(user_id, "volume", True)
    elif "не нужно" in message.text.lower():
        storage.save(user_id, "volume", False)
    else:
        await message.answer("Пожалуйста, выберите вариант из списка:", reply_markup=get_volume_menu())
        return

    hair_type = storage.get(user_id, "hair_type")

    if hair_type == "colored":
        await message.answer("Уточните цвет волос:", reply_markup=get_hair_color_menu())
        await Form.color.set()
    else:
        await send_hair_recommendation(message, state)

@dp.message_handler(state=Form.color)
async def color_handler(message: types.Message, state: FSMContext):
    """Обработка выбора цвета волос"""
    if message.text not in ["Шатенка", "Русая", "Рыжая", "Другой"]:
        await message.answer("Пожалуйста, выберите вариант из списка:", reply_markup=get_hair_color_menu())
        return

    storage.save(message.from_user.id, "color", message.text)
    await send_hair_recommendation(message, state)

async def send_hair_recommendation(message: types.Message, state: FSMContext):
    """Формирование и отправка рекомендации для волос (с изображениями)"""
    user_id = message.from_user.id
    data = storage.get(user_id)

    if not data:
        await message.answer("Произошла ошибка. Давайте начнём заново:", reply_markup=get_main_menu())
        await Form.main.set()
        return

    hair_type = data.get("hair_type", "colored")
    base_rec = HAIR_BASE_RECOMMENDATIONS.get(hair_type, HAIR_BASE_RECOMMENDATIONS["colored"])
    
    # Начинаем с базового ухода
    response = [base_rec["title"]]
    response.extend(base_rec["products"])
    
    # Добавляем проблемы
    problems = data.get("problems", [])
    if problems and 'none' not in problems:
        for prob in problems:
            if prob in HAIR_PROBLEMS_RECOMMENDATIONS:
                response.append(f"\n{HAIR_PROBLEMS_RECOMMENDATIONS[prob]['title']}")
                response.extend(HAIR_PROBLEMS_RECOMMENDATIONS[prob]["products"])
    
    # Чувствительная кожа головы
    if data.get("scalp"):
        response.append(f"\n{SENSITIVE_SCALP_RECOMMENDATION['title']}")
        response.extend(SENSITIVE_SCALP_RECOMMENDATION["products"])
    
    # Объем
    if data.get("volume"):
        response.append(f"\n{VOLUME_RECOMMENDATION['title']}")
        response.extend(VOLUME_RECOMMENDATION["products"])
    
    # Цветовые маски
    if hair_type == "colored":
        hair_color = data.get("color", "")
        if hair_color in COLOR_MASKS:
            response.append(f"\n{COLOR_MASKS[hair_color]['title']}")
            response.extend(COLOR_MASKS[hair_color]["products"])
    
    # Итог
    response.append(f"\n\n{LOCATIONS}\n\n{REC_DELIVERY_TEXT}")
    response.append(f"\n🔄 *Для нового подбора нажмите «Начать заново»*")
    
    # Используем изображение базового ухода как основное
    main_image = base_rec.get("image", "https://via.placeholder.com/400x200/000000/FFF?text=Уход+за+волосами")
    
    try:
        await message.answer_photo(
            photo=main_image,
            caption="\n".join(response),
            reply_markup=get_final_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        await message.answer("\n".join(response), reply_markup=get_final_menu())
    
    await Form.result.set()

# ========== ФИНАЛЬНЫЕ ДЕЙСТВИЯ ==========

@dp.message_handler(text="📍 Точки продаж", state='*')
async def show_locations(message: types.Message):
    """Показать точки продаж"""
    await message.answer(LOCATIONS, reply_markup=get_final_menu())

@dp.message_handler(text="🚚 Заказать доставку", state='*')
async def show_delivery(message: types.Message):
    """Показать информацию о доставке"""
    await message.answer(REC_DELIVERY_TEXT, reply_markup=get_final_menu())

@dp.message_handler(text="🔄 Новый подбор", state='*')
async def new_selection(message: types.Message, state: FSMContext):
    """Новый подбор"""
    await cmd_start(message, state)

# ========== ОБРАБОТКА НЕИЗВЕСТНЫХ СООБЩЕНИЙ ==========

@dp.message_handler(state='*')
async def unknown_message(message: types.Message):
    """Обработка неизвестных сообщений"""
    await message.answer(
        "Пожалуйста, используйте кнопки для навигации.\n"
        "Если хотите начать заново, нажмите /start",
        reply_markup=get_main_menu()
    )

# ========== ЗАПУСК БОТА ==========

async def on_startup(dp):
    """Действия при запуске бота"""
    logger.info("✅ Бот успешно запущен!")
    print("=" * 50)
    print("🤖 БОТ РАБОТАЕТ НА RENDER.COM!")
    print("=" * 50)

async def on_shutdown(dp):
    """Действия при остановке бота"""
    logger.info("Бот остановлен")

if __name__ == '__main__':
    executor.start_polling(
        dp, 
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )
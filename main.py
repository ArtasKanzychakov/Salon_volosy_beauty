import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor

from config import BOT_TOKEN, WELCOME_TEXT, EMOJI, LOCATIONS_TEXT, DELIVERY_TEXT
from keyboards import *
from database import storage

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

# ========== РЕКОМЕНДАЦИИ ==========

BODY_RECOMMENDATIONS = {
    "Общий уход и увлажнение": [
        "• Молочко для тела",
        "• Гидрофильное масло",
        "• Крем-суфле",
        "• Скраб кофе/кокос",
        "• Гель для душа (вишня/манго/лимон)",
        "• + Гиалуроновая кислота для лица"
    ],
    "Сухая кожа": [
        "• Гидрофильное масло",
        "• Баттер для тела",
        "• + Гиалуроновая кислота для лица"
    ],
    "Чувствительная кожа": [
        "• Гель для душа (вишня/манго/лимон)",
        "• Молочко для тела",
        "• Гидрофильное масло",
        "• + Гиалуроновая кислота для лица"
    ],
    "Борьба с целлюлитом": [
        "• Гель для душа (вишня/манго/лимон)",
        "• Антицеллюлитный скраб (мята)",
        "• Скраб кофе/кокос",
        "• Молочко для тела",
        "• + Гиалуроновая кислота для лица"
    ]
}

HAIR_BASE_RECOMMENDATIONS = {
    "blonde": [
        "• Шампунь для осветленных волос с гиалуроновой кислотой",
        "• Кондиционер для осветленных волос с гиалуроновой кислотой",
        "• Маска для осветленных волос с гиалуроновой кислотой",
        "• Биолипидный спрей",
        "• Молочко для волос"
    ],
    "colored": [
        "• Шампунь для окрашенных волос с коллагеном",
        "• Кондиционер для окрашенных волос с коллагеном",
        "• Маска для окрашенных волос с коллагеном",
        "• Биолипидный спрей"
    ],
    "natural": [
        "• Шампунь «Укрепление и сила»",
        "• Кондиционер «Укрепление и сила»",
        "• Маска «Укрепление и сила»",
        "• Биолипидный спрей",
        "• Спрей «Укрепление и сила»",
        "• Протеиновый крем"
    ]
}

HAIR_PROBLEMS_RECOMMENDATIONS = {
    "brittle": ["• Биолипидный спрей", "• Флюид для волос", "• Масло ELIXIR"],
    "hair_loss": ["• Шампунь против выпадения", "• Лосьон для роста волос"],
    "dandruff": ["• Шампунь против перхоти"],
    "split_ends": ["• Масло ELIXIR"],
    "dull": ["• Молочко для волос", "• Масло концентрат"],
    "frizzy": ["• Флюид для волос", "• Протеиновый крем", "• Масло ELIXIR"],
    "thin": ["• Шампунь для тонких волос", "• Кондиционер для тонких волос", "• Маска «Укрепление и сила»"],
    "damaged": ["• Шампунь реконстракт", "• Маска реконстракт", "• Биолипидный спрей", "• Флюид для волос", "• Масло ELIXIR"]
}

VOLUME_RECOMMENDATION = [
    "• Шампунь для тонких волос «Укрепление и сила»",
    "• Кондиционер для тонких волос «Укрепление и сила»",
    "• Маска «Укрепление и сила»",
    "• Спрей «Укрепление и сила»",
    "• Биолипидный спрей"
]

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

@dp.message_handler(commands=['start', 'restart'], state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик старта"""
    await state.finish()
    storage.delete(message.from_user.id)
    
    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu())
    await Form.main.set()

@dp.message_handler(text=f"{EMOJI['restart']} Начать заново", state='*')
async def cmd_restart(message: types.Message, state: FSMContext):
    """Обработчик перезапуска"""
    await cmd_start(message, state)

@dp.message_handler(text=f"{EMOJI['back']} Назад", state='*')
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

@dp.message_handler(text=f"{EMOJI['body']} Уход за телом", state=Form.main)
async def body_care_handler(message: types.Message):
    """Выбран уход за телом"""
    await message.answer("Выберите задачу для кожи тела:", reply_markup=get_body_care_menu())
    await Form.body.set()

@dp.message_handler(text=f"{EMOJI['hair']} Уход за волосами", state=Form.main)
async def hair_care_handler(message: types.Message):
    """Выбран уход за волосами"""
    await message.answer("Ваши волосы окрашены?", reply_markup=get_hair_type_menu())
    await Form.hair_type.set()

# ========== УХОД ЗА ТЕЛОМ ==========

@dp.message_handler(state=Form.body)
async def body_type_handler(message: types.Message, state: FSMContext):
    """Обработка выбора типа кожи тела"""
    text = message.text
    
    # Определяем тип по тексту кнопки
    if "Общий уход" in text:
        body_type = "Общий уход и увлажнение"
    elif "Сухая кожа" in text:
        body_type = "Сухая кожа"
    elif "Чувствительная кожа" in text:
        body_type = "Чувствительная кожа"
    elif "Борьба с целлюлитом" in text:
        body_type = "Борьба с целлюлитом"
    else:
        await message.answer("Пожалуйста, выберите вариант из списка:", reply_markup=get_body_care_menu())
        return
    
    # Формируем рекомендацию
    products = BODY_RECOMMENDATIONS.get(body_type, [])
    
    response = f"""
{EMOJI['recommendation']} *Ваша персонализированная рекомендация*

*{body_type}:*

{chr(10).join(products)}

{LOCATIONS_TEXT}

{DELIVERY_TEXT}

{EMOJI['restart']} *Для нового подбора нажмите «Начать заново»*
    """
    
    await message.answer(response, reply_markup=get_final_menu())
    await Form.result.set()

# ========== УХОД ЗА ВОЛОСАМИ ==========

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
    
    # Сохраняем тип волос
    storage.save(message.from_user.id, "hair_type", hair_type)
    
    # Просим выбрать проблемы
    await message.answer(f"{EMOJI['problem']} Выберите проблемы волос (можно несколько):", reply_markup=get_back_menu())
    await message.answer("Нажмите на проблему для выбора:", reply_markup=get_problems_inline_keyboard())
    await Form.problems.set()

@dp.callback_query_handler(lambda c: c.data.startswith('problem_'), state=Form.problems)
async def process_problem_callback(callback_query: types.CallbackQuery):
    """Обработка выбора проблемы"""
    problem_id = callback_query.data.replace('problem_', '')
    user_id = callback_query.from_user.id
    
    # Получаем текущий список проблем
    current_problems = storage.get(user_id, "problems") or []
    
    if problem_id == 'none':
        # Если выбрано "Ничего из перечисленного", очищаем все
        current_problems = ['none']
    elif problem_id in current_problems:
        # Убираем проблему, если она уже выбрана
        current_problems.remove(problem_id)
        if 'none' in current_problems:
            current_problems.remove('none')
    else:
        # Добавляем проблему
        if 'none' in current_problems:
            current_problems = []
        current_problems.append(problem_id)
    
    # Сохраняем обновлённый список
    storage.save(user_id, "problems", current_problems)
    
    # Обновляем клавиатуру
    await bot.edit_message_reply_markup(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=get_problems_inline_keyboard(current_problems)
    )
    
    await bot.answer_callback_query(callback_query.id)

@dp.callback_query_handler(lambda c: c.data == 'problems_done', state=Form.problems)
async def problems_done_handler(callback_query: types.CallbackQuery):
    """Завершение выбора проблем"""
    user_id = callback_query.from_user.id
    problems = storage.get(user_id, "problems")
    
    if not problems:
        await bot.answer_callback_query(callback_query.id, "Выберите хотя бы одну проблему или 'Ничего из перечисленного'")
        return
    
    await bot.answer_callback_query(callback_query.id, "Выбор сохранён!")
    await bot.send_message(callback_query.message.chat.id, "Есть ли чувствительная кожа головы?", reply_markup=get_yes_no_menu())
    await Form.scalp.set()

@dp.message_handler(state=Form.scalp)
async def scalp_handler(message: types.Message):
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
    
    # Проверяем тип волос
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
    """Формирование и отправка рекомендации для волос"""
    user_id = message.from_user.id
    data = storage.get(user_id)
    
    if not data:
        await message.answer("Произошла ошибка. Давайте начнём заново:", reply_markup=get_main_menu())
        await Form.main.set()
        return
    
    response = [f"{EMOJI['recommendation']} *Ваш набор для волос:*\n"]
    
    # 1. Базовый уход
    hair_type = data.get("hair_type", "colored")
    base_products = HAIR_BASE_RECOMMENDATIONS.get(hair_type, HAIR_BASE_RECOMMENDATIONS["colored"])
    
    response.append(f"\n{EMOJI['hair']} *Базовый уход:*")
    response.extend(base_products)
    
    # 2. Проблемы
    problems = data.get("problems", [])
    if problems and 'none' not in problems:
        response.append(f"\n{EMOJI['problem']} *Для проблем:*")
        for prob in problems:
            if prob in HAIR_PROBLEMS_RECOMMENDATIONS:
                response.extend(HAIR_PROBLEMS_RECOMMENDATIONS[prob])
    
    # 3. Чувствительная кожа головы
    if data.get("scalp"):
        response.append(f"\n😌 *Для чувствительной кожи головы:*")
        response.append("• Шампунь для чувствительной кожи головы")
    
    # 4. Объем
    if data.get("volume"):
        response.append(f"\n📈 *Для объема:*")
        response.extend(VOLUME_RECOMMENDATION)
    
    # 5. Цветовые маски (только для окрашенных)
    if hair_type == "colored":
        hair_color = data.get("color", "")
        if hair_color in ["Шатенка", "Русая"]:
            response.append(f"\n🎨 *Для вашего цвета:*")
            response.append("• Оттеночная маска «Холодный шоколад»")
        elif hair_color == "Рыжая":
            response.append(f"\n🎨 *Для вашего цвета:*")
            response.append("• Оттеночная маска «Медный»")
    
    # 6. Итог
    response.append(f"\n\n{LOCATIONS_TEXT}\n\n{DELIVERY_TEXT}")
    response.append(f"\n{EMOJI['restart']} *Для нового подбора нажмите «Начать заново»*")
    
    await message.answer("\n".join(response), reply_markup=get_final_menu())
    await Form.result.set()

# ========== ФИНАЛЬНЫЕ ДЕЙСТВИЯ ==========

@dp.message_handler(text=f"{EMOJI['location']} Точки продаж", state='*')
async def show_locations(message: types.Message):
    """Показать точки продаж"""
    await message.answer(LOCATIONS_TEXT, reply_markup=get_final_menu())

@dp.message_handler(text=f"{EMOJI['delivery']} Заказать доставку", state='*')
async def show_delivery(message: types.Message):
    """Показать информацию о доставке"""
    await message.answer(DELIVERY_TEXT, reply_markup=get_final_menu())

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
    
    # Отправляем сообщение администратору
    from config import ADMIN_ID
    if ADMIN_ID:
        try:
            await bot.send_message(ADMIN_ID, "🤖 Бот успешно запущен и готов к работе!")
        except:
            pass

async def on_shutdown(dp):
    """Действия при остановке бота"""
    logger.info("Бот остановлен")
    await bot.close()

if __name__ == '__main__':
    # Запускаем поллинг (стабильно для Render.com)
    executor.start_polling(
        dp, 
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )
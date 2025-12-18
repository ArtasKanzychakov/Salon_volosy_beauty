import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor

from config import BOT_TOKEN
from keyboards import *
from database import storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher(bot, storage=MemoryStorage())

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

BODY = {
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

HAIR_BASE = {
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

HAIR_PROBLEMS = {
    "brittle": ["• Биолипидный спрей", "• Флюид для волос", "• Масло ELIXIR"],
    "hair_loss": ["• Шампунь против выпадения", "• Лосьон для роста волос"],
    "dandruff": ["• Шампунь против перхоти"],
    "split_ends": ["• Масло ELIXIR"],
    "dull": ["• Молочко для волос", "• Масло концентрат"],
    "frizzy": ["• Флюид для волос", "• Протеиновый крем", "• Масло ELIXIR"],
    "thin": ["• Шампунь для тонких волос", "• Кондиционер для тонких волос", "• Маска «Укрепление и сила»"],
    "damaged": ["• Шампунь реконстракт", "• Маска реконстракт", "• Биолипидный спрей", "• Флюид для волос", "• Масло ELIXIR"]
}

VOLUME = [
    "• Шампунь для тонких волос «Укрепление и сила»",
    "• Кондиционер для тонких волос «Укрепление и сила»",
    "• Маска «Укрепление и сила»",
    "• Спрей «Укрепление и сила»",
    "• Биолипидный спрей"
]

LOCATIONS = """
📍 *Точки продаж:*

• *Салон красоты COLORIST*, Лермонтова 21
  ⌚ 9:00–20:00, без выходных

• *ТЦ Европа*, 1 этаж, отдел ZOOM Box  
  ⌚ 10:00–21:00, без выходных

• *ТЦ Калина*, 1 этаж, отдел Dark point
  ⌚ 10:00–21:00, без выходных
"""

DELIVERY = """
🚚 *Заказать доставку:*

Напишите в Telegram:
👉 @SVOY_AVCOSMETIC
"""

# ========== КОМАНДЫ ==========

@dp.message_handler(commands=['start', 'restart'], state='*')
async def start_cmd(message: types.Message, state: FSMContext):
    await state.finish()
    storage.delete(message.from_user.id)
    await message.answer("👋 Привет! Я помогу подобрать уход.\nВыберите категорию:", reply_markup=main_menu())
    await Form.main.set()

@dp.message_handler(text="◀️ Назад", state='*')
async def back_cmd(message: types.Message, state: FSMContext):
    current = await state.get_state()
    
    if current == Form.body.state:
        await message.answer("Главное меню:", reply_markup=main_menu())
        await Form.main.set()
    elif current in [Form.hair_type.state, Form.problems.state, Form.scalp.state, Form.volume.state, Form.color.state]:
        await message.answer("Главное меню:", reply_markup=main_menu())
        await Form.main.set()
    else:
        await start_cmd(message, state)

@dp.message_handler(text="🔄 Начать заново", state='*')
async def restart_cmd(message: types.Message, state: FSMContext):
    await start_cmd(message, state)

# ========== ГЛАВНОЕ МЕНЮ ==========

@dp.message_handler(text="🧴 Уход за телом", state=Form.main)
async def body_start(message: types.Message):
    await message.answer("Выберите задачу для кожи тела:", reply_markup=body_care())
    await Form.body.set()

@dp.message_handler(text="💇‍♀️ Уход за волосами", state=Form.main)
async def hair_start(message: types.Message):
    await message.answer("Ваши волосы окрашены?", reply_markup=hair_type())
    await Form.hair_type.set()

# ========== ТЕЛО ==========

@dp.message_handler(state=Form.body)
async def body_choice(message: types.Message, state: FSMContext):
    choice = message.text
    
    if choice not in BODY:
        await message.answer("Выберите вариант из списка:", reply_markup=body_care())
        return
    
    response = f"🧴 *Рекомендация для {choice}:*\n\n" + "\n".join(BODY[choice])
    response += f"\n\n{LOCATIONS}\n\n{DELIVERY}"
    
    await message.answer(response, reply_markup=final_actions())
    await Form.result.set()

# ========== ВОЛОСЫ ==========

@dp.message_handler(state=Form.hair_type)
async def hair_type_choice(message: types.Message, state: FSMContext):
    text = message.text
    
    if "блондинка" in text:
        hair = "blonde"
    elif "Окрашенные" in text:
        hair = "colored"
    elif "Натуральные" in text:
        hair = "natural"
    else:
        await message.answer("Выберите вариант:", reply_markup=hair_type())
        return
    
    storage.save(message.from_user.id, "hair_type", hair)
    
    await message.answer("Выберите проблемы волос (можно несколько):", reply_markup=back_button())
    await message.answer("Нажмите на проблему для выбора:", reply_markup=problems_keyboard())
    await Form.problems.set()

@dp.callback_query_handler(lambda c: c.data.startswith('prob_'), state=Form.problems)
async def problem_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    problem = callback.data.replace('prob_', '')
    
    current = storage.get(user_id, "problems") or []
    
    if problem == "none":
        current = ["none"]
    elif problem in current:
        current.remove(problem)
        if "none" in current:
            current.remove("none")
    else:
        if "none" in current:
            current = []
        current.append(problem)
    
    storage.save(user_id, "problems", current)
    
    await callback.message.edit_reply_markup(reply_markup=problems_keyboard(current))
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'done', state=Form.problems)
async def problems_done(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    problems = storage.get(user_id, "problems")
    
    if not problems:
        await callback.answer("Выберите хотя бы одну проблему или 'Нет проблем'")
        return
    
    await callback.answer("Сохранено!")
    await callback.message.answer("Есть ли чувствительная кожа головы?", reply_markup=yes_no())
    await Form.scalp.set()

@dp.message_handler(state=Form.scalp)
async def scalp_choice(message: types.Message):
    if message.text not in ["Да", "Нет"]:
        await message.answer("Ответьте Да или Нет:", reply_markup=yes_no())
        return
    
    storage.save(message.from_user.id, "scalp", message.text == "Да")
    
    await message.answer("Нужен дополнительный объем?", reply_markup=volume())
    await Form.volume.set()

@dp.message_handler(state=Form.volume)
async def volume_choice(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    hair_type = storage.get(user_id, "hair_type")
    
    if "хочу объем" in message.text.lower():
        storage.save(user_id, "volume", True)
    elif "не нужно" in message.text.lower():
        storage.save(user_id, "volume", False)
    else:
        await message.answer("Выберите вариант:", reply_markup=volume())
        return
    
    if hair_type == "colored":
        await message.answer("Уточните цвет волос:", reply_markup=hair_color())
        await Form.color.set()
    else:
        await send_hair_result(message, state)

@dp.message_handler(state=Form.color)
async def color_choice(message: types.Message, state: FSMContext):
    if message.text not in ["Шатенка", "Русая", "Рыжая", "Другой"]:
        await message.answer("Выберите цвет:", reply_markup=hair_color())
        return
    
    storage.save(message.from_user.id, "color", message.text)
    await send_hair_result(message, state)

async def send_hair_result(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = storage.get(user_id)
    
    response = ["💇‍♀️ *Ваш набор для волос:*\n"]
    
    # Базовый уход
    hair_type = data.get("hair_type", "colored")
    response.append("\n*Базовый уход:*")
    response.extend(HAIR_BASE.get(hair_type, HAIR_BASE["colored"]))
    
    # Проблемы
    problems = data.get("problems", [])
    if problems and "none" not in problems:
        response.append("\n*Для проблем:*")
        for prob in problems:
            if prob in HAIR_PROBLEMS:
                response.extend(HAIR_PROBLEMS[prob])
    
    # Кожа головы
    if data.get("scalp"):
        response.append("\n*Для чувствительной кожи:*")
        response.append("• Шампунь для чувствительной кожи головы")
    
    # Объем
    if data.get("volume"):
        response.append("\n*Для объема:*")
        response.extend(VOLUME)
    
    # Цвет
    color = data.get("color", "")
    if color in ["Шатенка", "Русая"]:
        response.append("\n*Для вашего цвета:*")
        response.append("• Оттеночная маска «Холодный шоколад»")
    elif color == "Рыжая":
        response.append("\n*Для вашего цвета:*")
        response.append("• Оттеночная маска «Медный»")
    
    # Итог
    response.append(f"\n\n{LOCATIONS}\n\n{DELIVERY}")
    
    await message.answer("\n".join(response), reply_markup=final_actions())
    await Form.result.set()

# ========== ФИНАЛЬНЫЕ КНОПКИ ==========

@dp.message_handler(text="📍 Точки продаж", state='*')
async def locations_cmd(message: types.Message):
    await message.answer(LOCATIONS, reply_markup=final_actions())

@dp.message_handler(text="🚚 Заказать доставку", state='*')
async def delivery_cmd(message: types.Message):
    await message.answer(DELIVERY, reply_markup=final_actions())

# ========== НЕИЗВЕСТНЫЕ СООБЩЕНИЯ ==========

@dp.message_handler(state='*')
async def unknown(message: types.Message):
    await message.answer("Используйте кнопки или /start", reply_markup=main_menu())

# ========== ЗАПУСК ==========

async def on_startup(_):
    logger.info("Бот запущен!")

async def on_shutdown(_):
    logger.info("Бот остановлен")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
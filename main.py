import asyncio
import logging
import os
from contextlib import suppress

from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery

from config import BOT_TOKEN, WELCOME_TEXT
from keyboards import (
    get_main_menu, get_body_care_menu, get_hair_type_menu,
    get_problems_inline_keyboard, get_yes_no_menu,
    get_volume_menu, get_hair_color_menu, get_final_menu
)
from database import storage
from recommendations import (
    BODY_CARE_RECOMMENDATIONS, HAIR_BASE_RECOMMENDATIONS,
    HAIR_PROBLEMS_RECOMMENDATIONS, VOLUME_RECOMMENDATION,
    SENSITIVE_SCALP_RECOMMENDATION, COLOR_MASKS,
    LOCATIONS, DELIVERY_TEXT as REC_DELIVERY_TEXT
)

# ========== НАСТРОЙКА ЛОГГИРОВАНИЯ ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== ИНИЦИАЛИЗАЦИЯ КОМПОНЕНТОВ БОТА ==========
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# ========== СОСТОЯНИЯ БОТА ==========
class Form(StatesGroup):
    main = State()
    body = State()
    hair_type = State()
    problems = State()
    scalp = State()
    volume = State()
    color = State()
    result = State()

# ========== ОСНОВНАЯ ЛОГИКА БОТА ==========

# ---- Старт и навигация ----
@router.message(CommandStart(), Command("restart"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    storage.delete(message.from_user.id)
    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu())
    await state.set_state(Form.main)

@router.message(F.text == "◀️ Назад")
async def cmd_back(message: Message, state: FSMContext):
    await state.clear()
    await cmd_start(message, state)

# ---- Главное меню ----
@router.message(F.text == "🧴 Уход за телом", F.state == Form.main)
async def body_care_handler(message: Message, state: FSMContext):
    await message.answer("Выберите задачу для кожи тела:", reply_markup=get_body_care_menu())
    await state.set_state(Form.body)

@router.message(F.text == "💇‍♀️ Уход за волосами", F.state == Form.main)
async def hair_care_handler(message: Message, state: FSMContext):
    await message.answer("Ваши волосы окрашены?", reply_markup=get_hair_type_menu())
    await state.set_state(Form.hair_type)

# ---- Уход за телом ----
@router.message(Form.body)
async def body_type_handler(message: Message, state: FSMContext):
    mapping = {
        "Общий уход и увлажнение": "general",
        "Сухая кожа": "dry",
        "Чувствительная кожа": "sensitive",
        "Борьба с целлюлитом": "cellulite"
    }
    
    if message.text not in mapping:
        await message.answer("Выберите вариант из списка:", reply_markup=get_body_care_menu())
        return
    
    rec_key = mapping[message.text]
    rec = BODY_CARE_RECOMMENDATIONS[rec_key]
    text = f"{rec['title']}\n\n" + "\n".join(rec['products']) + f"\n\n{LOCATIONS}\n\n{REC_DELIVERY_TEXT}"
    
    try:
        await message.answer_photo(rec["image"], caption=text, reply_markup=get_final_menu())
    except:
        await message.answer(text, reply_markup=get_final_menu())
    
    await state.set_state(Form.result)

# ---- Уход за волосами ----
@router.message(Form.hair_type)
async def hair_type_handler(message: Message, state: FSMContext):
    text = message.text.lower()
    if "блондинка" in text:
        hair_type = "blonde"
    elif "окрашенные" in text:
        hair_type = "colored"
    elif "натуральные" in text:
        hair_type = "natural"
    else:
        await message.answer("Выберите вариант из списка:", reply_markup=get_hair_type_menu())
        return
    
    storage.save(message.from_user.id, "hair_type", hair_type)
    await message.answer("Выберите проблемы волос:", reply_markup=get_problems_inline_keyboard())
    await state.set_state(Form.problems)

@router.callback_query(F.data.startswith("prob_"), Form.problems)
async def process_problem(callback: CallbackQuery, state: FSMContext):
    prob_id = callback.data.replace("prob_", "")
    user_id = callback.from_user.id
    problems = storage.get(user_id, "problems") or []
    
    if prob_id == "none":
        problems = ["none"]
    elif prob_id in problems:
        problems.remove(prob_id)
        if "none" in problems:
            problems.remove("none")
    else:
        if "none" in problems:
            problems = []
        problems.append(prob_id)
    
    storage.save(user_id, "problems", problems)
    await callback.message.edit_reply_markup(reply_markup=get_problems_inline_keyboard(problems))
    await callback.answer()

@router.callback_query(F.data == "done", Form.problems)
async def problems_done(callback: CallbackQuery, state: FSMContext):
    problems = storage.get(callback.from_user.id, "problems")
    if not problems:
        await callback.answer("Выберите хотя бы одну проблему", show_alert=True)
        return
    
    await callback.answer("Сохранено!")
    await callback.message.answer("Есть ли чувствительная кожа головы?", reply_markup=get_yes_no_menu())
    await state.set_state(Form.scalp)

@router.message(Form.scalp)
async def scalp_handler(message: Message, state: FSMContext):
    if message.text not in ["Да", "Нет"]:
        await message.answer("Ответьте Да или Нет:", reply_markup=get_yes_no_menu())
        return
    
    storage.save(message.from_user.id, "scalp", message.text == "Да")
    await message.answer("Нужен дополнительный объем?", reply_markup=get_volume_menu())
    await state.set_state(Form.volume)

@router.message(Form.volume)
async def volume_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if "хочу объем" in message.text.lower():
        storage.save(user_id, "volume", True)
    elif "не нужно" in message.text.lower():
        storage.save(user_id, "volume", False)
    else:
        await message.answer("Выберите вариант из списка:", reply_markup=get_volume_menu())
        return
    
    hair_type = storage.get(user_id, "hair_type")
    if hair_type == "colored":
        await message.answer("Уточните цвет волос:", reply_markup=get_hair_color_menu())
        await state.set_state(Form.color)
    else:
        await send_hair_final(message, state)

@router.message(Form.color)
async def color_handler(message: Message, state: FSMContext):
    if message.text not in ["Шатенка", "Русая", "Рыжая", "Другой"]:
        await message.answer("Выберите вариант из списка:", reply_markup=get_hair_color_menu())
        return
    
    storage.save(message.from_user.id, "color", message.text)
    await send_hair_final(message, state)

async def send_hair_final(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = storage.get(user_id)
    
    if not data:
        await cmd_start(message, state)
        return
    
    rec_parts = []
    hair_type = data.get("hair_type", "colored")
    base_rec = HAIR_BASE_RECOMMENDATIONS.get(hair_type, HAIR_BASE_RECOMMENDATIONS["colored"])
    
    rec_parts.append(base_rec["title"])
    rec_parts.extend(base_rec["products"])
    
    problems = data.get("problems", [])
    if problems and 'none' not in problems:
        for prob in problems:
            if prob in HAIR_PROBLEMS_RECOMMENDATIONS:
                rec_parts.append("")
                rec_parts.append(HAIR_PROBLEMS_RECOMMENDATIONS[prob]["title"])
                rec_parts.extend(HAIR_PROBLEMS_RECOMMENDATIONS[prob]["products"])
    
    if data.get("scalp"):
        rec_parts.append("")
        rec_parts.append(SENSITIVE_SCALP_RECOMMENDATION["title"])
        rec_parts.extend(SENSITIVE_SCALP_RECOMMENDATION["products"])
    
    if data.get("volume"):
        rec_parts.append("")
        rec_parts.append(VOLUME_RECOMMENDATION["title"])
        rec_parts.extend(VOLUME_RECOMMENDATION["products"])
    
    if hair_type == "colored":
        color = data.get("color", "")
        if color in COLOR_MASKS:
            rec_parts.append("")
            rec_parts.append(COLOR_MASKS[color]["title"])
            rec_parts.extend(COLOR_MASKS[color]["products"])
    
    final_text = "\n".join(rec_parts)
    final_text += f"\n\n{LOCATIONS}\n\n{REC_DELIVERY_TEXT}\n\n🔄 Для нового подбора нажмите «Новый подбор»"
    
    try:
        await message.answer_photo(base_rec["image"], caption=final_text, reply_markup=get_final_menu())
    except Exception as e:
        logger.error(f"Фото не отправлено: {e}")
        await message.answer(final_text, reply_markup=get_final_menu())
    
    await state.set_state(Form.result)

# ---- Финальные действия ----
@router.message(F.text == "📍 Точки продаж")
async def show_locations(message: Message):
    await message.answer(LOCATIONS, reply_markup=get_final_menu())

@router.message(F.text == "🚚 Заказать доставку")
async def show_delivery(message: Message):
    await message.answer(REC_DELIVERY_TEXT, reply_markup=get_final_menu())

@router.message(F.text == "🔄 Новый подбор")
async def new_search(message: Message, state: FSMContext):
    await cmd_start(message, state)

# ---- Неизвестные сообщения ----
@router.message()
async def unknown(message: Message):
    await message.answer("Используйте кнопки или команду /start", reply_markup=get_main_menu())

# ========== HTTP-СЕРВЕР ДЛЯ RENDER ==========
async def health_check(request):
    """Простой обработчик для проверки здоровья сервиса."""
    return web.Response(text="✅ Бот работает")

async def start_bot(app):
    """Запускает бота как фоновую задачу."""
    logger.info("🚀 Запуск Telegram бота...")
    # Удаляем старые обновления и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем поллинг в фоне
    app['bot_polling'] = asyncio.create_task(dp.start_polling(bot))
    logger.info("🤖 Бот запущен и готов к работе")

async def cleanup_bot(app):
    """Корректно останавливает бота при завершении работы."""
    logger.info("🛑 Остановка бота...")
    # Отменяем задачу поллинга
    if 'bot_polling' in app:
        app['bot_polling'].cancel()
        # Ждем отмены, игнорируя исключение CancelledError
        with suppress(asyncio.CancelledError):
            await app['bot_polling']
    # Закрываем сессию бота
    await bot.session.close()
    logger.info("Бот остановлен")

def create_web_app():
    """Создает и настраивает веб-приложение."""
    app = web.Application()
    # Добавляем маршруты для проверки здоровья
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    # Настраиваем запуск и остановку бота
    app.on_startup.append(start_bot)
    app.on_cleanup.append(cleanup_bot)
    
    return app

# ========== ТОЧКА ВХОДА ==========
def main():
    """Основная функция запуска приложения."""
    print("=" * 50)
    print("🚀 ЗАПУСК ПРИЛОЖЕНИЯ НА RENDER.COM")
    print("=" * 50)
    
    # Получаем порт из переменной окружения (Render устанавливает его)
    port = int(os.environ.get("PORT", 8080))
    
    # Создаем и запускаем веб-приложение
    app = create_web_app()
    web.run_app(app, host='0.0.0.0', port=port)

if __name__ == "__main__":
    main()
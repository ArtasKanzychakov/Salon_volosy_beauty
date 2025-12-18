import asyncio
import logging
import os
import signal
import sys
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

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
# Включаем подробное логирование для отладки
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Для максимальной детализации раскомментируйте строку ниже
# logging.getLogger('aiogram').setLevel(logging.DEBUG)

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
    """Обработчик команд /start и /restart"""
    logger.info(f"Команда /start от пользователя {message.from_user.id}")
    await state.clear()
    storage.delete(message.from_user.id)
    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu())
    await state.set_state(Form.main)
    logger.info(f"Состояние установлено в Form.main для пользователя {message.from_user.id}")

@router.message(F.text == "◀️ Назад")
async def cmd_back(message: Message, state: FSMContext):
    """Обработчик кнопки Назад"""
    logger.info(f"Кнопка 'Назад' от пользователя {message.from_user.id}")
    await state.clear()
    await cmd_start(message, state)

# ---- Главное меню ----
@router.message(F.text == "🧴 Уход за телом", F.state == Form.main)
async def body_care_handler(message: Message, state: FSMContext):
    """Обработчик кнопки 'Уход за телом'"""
    logger.info(f"Выбран 'Уход за телом' пользователем {message.from_user.id}")
    await message.answer("Выберите задачу для кожи тела:", reply_markup=get_body_care_menu())
    await state.set_state(Form.body)

@router.message(F.text == "💇‍♀️ Уход за волосами", F.state == Form.main)
async def hair_care_handler(message: Message, state: FSMContext):
    """Обработчик кнопки 'Уход за волосами'"""
    logger.info(f"Выбран 'Уход за волосами' пользователем {message.from_user.id}")
    await message.answer("Ваши волосы окрашены?", reply_markup=get_hair_type_menu())
    await state.set_state(Form.hair_type)

# ---- Уход за телом ----
@router.message(Form.body)
async def body_type_handler(message: Message, state: FSMContext):
    """Обработчик выбора типа ухода за телом"""
    logger.info(f"Обработка выбора ухода за телом: {message.text}")
    
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
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        await message.answer(text, reply_markup=get_final_menu())
    
    await state.set_state(Form.result)

# ---- Уход за волосами ----
@router.message(Form.hair_type)
async def hair_type_handler(message: Message, state: FSMContext):
    """Обработчик выбора типа волос"""
    logger.info(f"Выбор типа волос: {message.text}")
    
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
    logger.info(f"Тип волос сохранен: {hair_type} для пользователя {message.from_user.id}")
    
    await message.answer("Выберите проблемы волос:", reply_markup=get_problems_inline_keyboard())
    await state.set_state(Form.problems)

@router.callback_query(F.data.startswith("prob_"), Form.problems)
async def process_problem(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора проблем волос"""
    prob_id = callback.data.replace("prob_", "")
    user_id = callback.from_user.id
    problems = storage.get(user_id, "problems") or []
    
    logger.info(f"Обработка проблемы {prob_id} для пользователя {user_id}, текущие проблемы: {problems}")
    
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
    await callback.answer(f"Проблема '{prob_id}' обновлена")

@router.callback_query(F.data == "done", Form.problems)
async def problems_done(callback: CallbackQuery, state: FSMContext):
    """Завершение выбора проблем"""
    user_id = callback.from_user.id
    problems = storage.get(user_id, "problems")
    
    logger.info(f"Завершение выбора проблем для пользователя {user_id}, выбранные проблемы: {problems}")
    
    if not problems:
        await callback.answer("Выберите хотя бы одну проблему", show_alert=True)
        return
    
    await callback.answer("Сохранено!")
    await callback.message.answer("Есть ли чувствительная кожа головы?", reply_markup=get_yes_no_menu())
    await state.set_state(Form.scalp)

@router.message(Form.scalp)
async def scalp_handler(message: Message, state: FSMContext):
    """Обработчик выбора типа кожи головы"""
    logger.info(f"Обработка выбора кожи головы: {message.text}")
    
    if message.text not in ["Да", "Нет"]:
        await message.answer("Ответьте Да или Нет:", reply_markup=get_yes_no_menu())
        return
    
    scalp_sensitive = message.text == "Да"
    storage.save(message.from_user.id, "scalp", scalp_sensitive)
    logger.info(f"Чувствительность кожи головы сохранена: {scalp_sensitive} для пользователя {message.from_user.id}")
    
    await message.answer("Нужен дополнительный объем?", reply_markup=get_volume_menu())
    await state.set_state(Form.volume)

@router.message(Form.volume)
async def volume_handler(message: Message, state: FSMContext):
    """Обработчик выбора объема"""
    user_id = message.from_user.id
    logger.info(f"Обработка выбора объема: {message.text}")
    
    if "хочу объем" in message.text.lower():
        storage.save(user_id, "volume", True)
        volume_needed = True
    elif "не нужно" in message.text.lower():
        storage.save(user_id, "volume", False)
        volume_needed = False
    else:
        await message.answer("Выберите вариант из списка:", reply_markup=get_volume_menu())
        return
    
    logger.info(f"Потребность в объеме сохранена: {volume_needed} для пользователя {user_id}")
    
    hair_type = storage.get(user_id, "hair_type")
    if hair_type == "colored":
        await message.answer("Уточните цвет волос:", reply_markup=get_hair_color_menu())
        await state.set_state(Form.color)
    else:
        await send_hair_final(message, state)

@router.message(Form.color)
async def color_handler(message: Message, state: FSMContext):
    """Обработчик выбора цвета волос"""
    logger.info(f"Обработка выбора цвета волос: {message.text}")
    
    if message.text not in ["Шатенка", "Русая", "Рыжая", "Другой"]:
        await message.answer("Выберите вариант из списка:", reply_markup=get_hair_color_menu())
        return
    
    storage.save(message.from_user.id, "color", message.text)
    logger.info(f"Цвет волос сохранен: {message.text} для пользователя {message.from_user.id}")
    
    await send_hair_final(message, state)

async def send_hair_final(message: Message, state: FSMContext):
    """Формирование и отправка финальной рекомендации для волос"""
    user_id = message.from_user.id
    data = storage.get(user_id)
    
    logger.info(f"Формирование финальной рекомендации для пользователя {user_id}, данные: {data}")
    
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
    """Показать точки продаж"""
    logger.info(f"Запрос точек продаж от пользователя {message.from_user.id}")
    await message.answer(LOCATIONS, reply_markup=get_final_menu())

@router.message(F.text == "🚚 Заказать доставку")
async def show_delivery(message: Message):
    """Показать информацию о доставке"""
    logger.info(f"Запрос доставки от пользователя {message.from_user.id}")
    await message.answer(REC_DELIVERY_TEXT, reply_markup=get_final_menu())

@router.message(F.text == "🔄 Новый подбор")
async def new_search(message: Message, state: FSMContext):
    """Новый подбор"""
    logger.info(f"Запрос нового подбора от пользователя {message.from_user.id}")
    await cmd_start(message, state)

# ---- Обработчик неизвестных сообщений ----
@router.message()
async def unknown(message: Message):
    """Обработчик неизвестных сообщений"""
    logger.info(f"Неизвестное сообщение от пользователя {message.from_user.id}: {message.text}")
    await message.answer("Используйте кнопки или команду /start", reply_markup=get_main_menu())

# ========== ПРОСТОЙ HTTP-СЕРВЕР ДЛЯ RENDER ==========
class HealthCheckHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP-запросов для проверки здоровья сервиса"""
    
    def do_GET(self):
        if self.path in ['/', '/health']:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Bot is alive and running')
            logger.info(f"HTTP: Health check from {self.client_address[0]}")
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Отключаем стандартное логирование HTTP-сервера
        pass

def run_http_server():
    """Запускает простой HTTP-сервер в отдельном потоке"""
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    
    logger.info(f"🌐 HTTP-сервер запущен на порту {port}")
    print(f"✅ HTTP-сервер запущен на порту {port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        logger.info("🌐 HTTP-сервер остановлен")

# ========== ОСНОВНАЯ ФУНКЦИЯ ЗАПУСКА БОТА ==========
async def run_bot():
    """Основная асинхронная функция для запуска бота"""
    logger.info("🚀 Запуск Telegram бота...")
    print("=" * 50)
    print("🚀 ЗАПУСК ТЕЛЕГРАМ БОТА")
    print("=" * 50)
    
    # Удаляем вебхук и запускаем поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🤖 Бот запущен и готов к работе")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
        raise

def main():
    """Главная функция запуска приложения"""
    # Запускаем HTTP-сервер в отдельном потоке (для Render)
    http_thread = Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Запускаем бота в основном потоке
    logger.info("Запуск основного цикла бота...")
    
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
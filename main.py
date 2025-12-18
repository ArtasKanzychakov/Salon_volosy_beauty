import asyncio
import logging
import os
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InputFile
from aiogram.enums import ParseMode

from config import BOT_TOKEN, WELCOME_TEXT, EMOJI
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

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# Состояния (упрощенные)
class UserState:
    MAIN = "main"
    BODY = "body"
    HAIR_TYPE = "hair_type"
    PROBLEMS = "problems"
    SCALP = "scalp"
    VOLUME = "volume"
    COLOR = "color"
    RESULT = "result"

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик старта"""
    await state.clear()
    storage.delete(message.from_user.id)
    
    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu())
    await state.set_state(UserState.MAIN)

@router.message(Command("restart"))
async def cmd_restart(message: Message, state: FSMContext):
    """Перезапуск"""
    await cmd_start(message, state)

@router.message(F.text == "◀️ Назад")
async def cmd_back(message: Message, state: FSMContext):
    """Назад"""
    current_state = await state.get_state()
    
    if current_state == UserState.BODY:
        await message.answer("Главное меню:", reply_markup=get_main_menu())
        await state.set_state(UserState.MAIN)
    elif current_state in [UserState.HAIR_TYPE, UserState.PROBLEMS, UserState.SCALP, 
                          UserState.VOLUME, UserState.COLOR, UserState.RESULT]:
        await message.answer("Главное меню:", reply_markup=get_main_menu())
        await state.set_state(UserState.MAIN)
    else:
        await cmd_start(message, state)

# ========== ГЛАВНОЕ МЕНЮ ==========

@router.message(F.text == "🧴 Уход за телом", UserState.MAIN)
async def body_care_handler(message: Message, state: FSMContext):
    """Выбран уход за телом"""
    await message.answer("Выберите задачу для кожи тела:", reply_markup=get_body_care_menu())
    await state.set_state(UserState.BODY)

@router.message(F.text == "💇‍♀️ Уход за волосами", UserState.MAIN)
async def hair_care_handler(message: Message, state: FSMContext):
    """Выбран уход за волосами"""
    await message.answer("Ваши волосы окрашены?", reply_markup=get_hair_type_menu())
    await state.set_state(UserState.HAIR_TYPE)

# ========== УХОД ЗА ТЕЛОМ ==========

@router.message(UserState.BODY)
async def body_type_handler(message: Message, state: FSMContext):
    """Обработка выбора типа кожи тела"""
    text = message.text
    
    # Определяем тип
    body_type_map = {
        "Общий уход и увлажнение": "general",
        "Сухая кожа": "dry",
        "Чувствительная кожа": "sensitive",
        "Борьба с целлюлитом": "cellulite"
    }
    
    if text not in body_type_map:
        await message.answer("Пожалуйста, выберите вариант из списка:", reply_markup=get_body_care_menu())
        return
    
    key = body_type_map[text]
    recommendation = BODY_CARE_RECOMMENDATIONS[key]
    
    # Формируем ответ
    products_text = "\n".join(recommendation["products"])
    
    response = f"""
{recommendation['title']}

{products_text}

{LOCATIONS}

{REC_DELIVERY_TEXT}

🔄 *Для нового подбора нажмите «Начать заново»*
    """
    
    # Пытаемся отправить с фото
    try:
        await message.answer_photo(
            photo=recommendation["image"],
            caption=response,
            reply_markup=get_final_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        await message.answer(response, reply_markup=get_final_menu())
    
    await state.set_state(UserState.RESULT)

# ========== УХОД ЗА ВОЛОСАМИ ==========

@router.message(UserState.HAIR_TYPE)
async def hair_type_handler(message: Message, state: FSMContext):
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
    await message.answer("🔧 Выберите проблемы волос (можно несколько):")
    await message.answer("Нажмите на проблему для выбора:", reply_markup=get_problems_inline_keyboard())
    await state.set_state(UserState.PROBLEMS)

@router.callback_query(F.data.startswith("prob_"), UserState.PROBLEMS)
async def process_problem_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора проблемы"""
    problem_id = callback.data.replace("prob_", "")
    user_id = callback.from_user.id
    
    current_problems = storage.get(user_id, "problems") or []
    
    if problem_id == "none":
        current_problems = ["none"]
    elif problem_id in current_problems:
        current_problems.remove(problem_id)
        if "none" in current_problems:
            current_problems.remove("none")
    else:
        if "none" in current_problems:
            current_problems = []
        current_problems.append(problem_id)
    
    storage.save(user_id, "problems", current_problems)
    
    # Обновляем клавиатуру
    await callback.message.edit_reply_markup(
        reply_markup=get_problems_inline_keyboard(current_problems)
    )
    await callback.answer()

@router.callback_query(F.data == "done", UserState.PROBLEMS)
async def problems_done_handler(callback: CallbackQuery, state: FSMContext):
    """Завершение выбора проблем"""
    user_id = callback.from_user.id
    problems = storage.get(user_id, "problems")
    
    if not problems:
        await callback.answer("Выберите хотя бы одну проблему или 'Нет проблем'", show_alert=True)
        return
    
    await callback.answer("Выбор сохранён!")
    await callback.message.answer("Есть ли чувствительная кожа головы?", reply_markup=get_yes_no_menu())
    await state.set_state(UserState.SCALP)

@router.message(UserState.SCALP)
async def scalp_handler(message: Message, state: FSMContext):
    """Обработка выбора типа кожи головы"""
    if message.text not in ["Да", "Нет"]:
        await message.answer("Пожалуйста, ответьте Да или Нет:", reply_markup=get_yes_no_menu())
        return
    
    storage.save(message.from_user.id, "scalp", message.text == "Да")
    await message.answer("Нужен дополнительный объем?", reply_markup=get_volume_menu())
    await state.set_state(UserState.VOLUME)

@router.message(UserState.VOLUME)
async def volume_handler(message: Message, state: FSMContext):
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
        await state.set_state(UserState.COLOR)
    else:
        await send_hair_recommendation(message, state)

@router.message(UserState.COLOR)
async def color_handler(message: Message, state: FSMContext):
    """Обработка выбора цвета волос"""
    if message.text not in ["Шатенка", "Русая", "Рыжая", "Другой"]:
        await message.answer("Пожалуйста, выберите вариант из списка:", reply_markup=get_hair_color_menu())
        return
    
    storage.save(message.from_user.id, "color", message.text)
    await send_hair_recommendation(message, state)

async def send_hair_recommendation(message: Message, state: FSMContext):
    """Формирование и отправка рекомендации для волос"""
    user_id = message.from_user.id
    data = storage.get(user_id)
    
    if not data:
        await message.answer("Произошла ошибка. Давайте начнём заново:", reply_markup=get_main_menu())
        await state.set_state(UserState.MAIN)
        return
    
    hair_type = data.get("hair_type", "colored")
    base_rec = HAIR_BASE_RECOMMENDATIONS.get(hair_type, HAIR_BASE_RECOMMENDATIONS["colored"])
    
    # Формируем ответ
    response = [base_rec["title"]]
    response.extend(base_rec["products"])
    
    # Проблемы
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
    
    # Отправляем с фото
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
    
    await state.set_state(UserState.RESULT)

# ========== ФИНАЛЬНЫЕ ДЕЙСТВИЯ ==========

@router.message(F.text == "📍 Точки продаж")
async def show_locations(message: Message):
    """Показать точки продаж"""
    await message.answer(LOCATIONS, reply_markup=get_final_menu())

@router.message(F.text == "🚚 Заказать доставку")
async def show_delivery(message: Message):
    """Показать информацию о доставке"""
    await message.answer(REC_DELIVERY_TEXT, reply_markup=get_final_menu())

@router.message(F.text == "🔄 Новый подбор")
async def new_selection(message: Message, state: FSMContext):
    """Новый подбор"""
    await cmd_start(message, state)

# ========== НЕИЗВЕСТНЫЕ СООБЩЕНИЯ ==========

@router.message()
async def unknown_message(message: Message):
    """Обработка неизвестных сообщений"""
    await message.answer(
        "Пожалуйста, используйте кнопки для навигации.\n"
        "Если хотите начать заново, нажмите /start",
        reply_markup=get_main_menu()
    )

# ========== ЗАПУСК БОТА ==========

async def main():
    """Основная функция запуска"""
    logger.info("🚀 Запуск бота...")
    
    # Удаляем вебхук (если есть) и запускаем поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
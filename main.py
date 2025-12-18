import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import ParseMode
from aiogram.utils import executor

from config import BOT_TOKEN, ADMIN_ID, WELCOME_TEXT, EMOJI
from keyboards import *
from states import UserState
from database import MemoryStorage as UserStorage
from recommendations import *

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Инициализация хранилища пользователей
user_storage = UserStorage()

# Словарь для перевода состояний в русские названия
STATE_NAMES = {
    'MAIN_MENU': 'Главное меню',
    'BODY_CARE': 'Уход за телом',
    'BODY_TYPE': 'Выбор типа кожи',
    'HAIR_CARE': 'Уход за волосами', 
    'HAIR_TYPE': 'Тип волос',
    'HAIR_PROBLEMS': 'Проблемы волос',
    'SCALP_TYPE': 'Кожа головы',
    'VOLUME_NEED': 'Объём',
    'HAIR_COLOR': 'Цвет волос'
}

# ========== ХЭНДЛЕРЫ ==========

@dp.message_handler(commands=['start', 'restart'], state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.finish()
    user_storage.delete_state(message.from_user.id)
    user_storage.delete_problems(message.from_user.id)
    
    await message.answer(
        WELCOME_TEXT,
        reply_markup=get_main_menu()
    )
    await UserState.MAIN_MENU.set()

@dp.message_handler(text=f"{EMOJI['restart']} Начать заново", state='*')
async def restart_handler(message: types.Message, state: FSMContext):
    """Обработчик кнопки "Начать заново" """
    await cmd_start(message, state)

@dp.message_handler(text=f"{EMOJI['back']} Назад", state='*')
async def back_handler(message: types.Message, state: FSMContext):
    """Обработчик кнопки "Назад" """
    current_state = await state.get_state()
    
    # Определяем предыдущее состояние
    if current_state == UserState.BODY_TYPE.state:
        await message.answer("Вы вернулись в главное меню:", reply_markup=get_main_menu())
        await UserState.MAIN_MENU.set()
    
    elif current_state == UserState.HAIR_TYPE.state:
        await message.answer("Вы вернулись в главное меню:", reply_markup=get_main_menu())
        await UserState.MAIN_MENU.set()
    
    elif current_state == UserState.HAIR_PROBLEMS.state:
        await message.answer(
            f"{EMOJI['step']} *Шаг 1 из 6: Тип волос*\n\nВаши волосы окрашены?",
            reply_markup=get_hair_type_keyboard(1, 6)
        )
        await UserState.HAIR_TYPE.set()
    
    elif current_state == UserState.SCALP_TYPE.state:
        await message.answer(
            f"{EMOJI['step']} *Шаг 2 из 6: Проблемы волос*\n\nВыберите проблемы, которые вас беспокоят:",
            reply_markup=get_back_button()
        )
        await message.answer("Нажмите на проблемы, чтобы выбрать:", reply_markup=get_hair_problems_inline_keyboard())
        await UserState.HAIR_PROBLEMS.set()
    
    elif current_state == UserState.VOLUME_NEED.state:
        await message.answer(
            f"{EMOJI['step']} *Шаг 4 из 6: Кожа головы*\n\nЕсть ли у вас чувствительная кожа головы?",
            reply_markup=get_scalp_keyboard(4, 6)
        )
        await UserState.SCALP_TYPE.set()
    
    elif current_state == UserState.HAIR_COLOR.state:
        await message.answer(
            f"{EMOJI['step']} *Шаг 5 из 6: Объём*\n\nХотите добавить средства для дополнительного объёма?",
            reply_markup=get_volume_keyboard(5, 6)
        )
        await UserState.VOLUME_NEED.set()
    
    else:
        await message.answer("Вы вернулись в главное меню:", reply_markup=get_main_menu())
        await UserState.MAIN_MENU.set()

# ========== ГЛАВНОЕ МЕНЮ ==========

@dp.message_handler(text=f"{EMOJI['body']} Уход за телом", state=UserState.MAIN_MENU)
async def body_care_handler(message: types.Message, state: FSMContext):
    """Выбран уход за телом"""
    await message.answer(
        f"{EMOJI['step']} *Шаг 1 из 2: Задача для кожи тела*\n\nКакую главную задачу для кожи тела вы решаете?",
        reply_markup=get_body_care_keyboard(1, 2)
    )
    await UserState.BODY_TYPE.set()

@dp.message_handler(text=f"{EMOJI['hair']} Уход за волосами", state=UserState.MAIN_MENU)
async def hair_care_handler(message: types.Message, state: FSMContext):
    """Выбран уход за волосами"""
    await message.answer(
        f"{EMOJI['step']} *Шаг 1 из 6: Тип волос*\n\nВаши волосы окрашены?",
        reply_markup=get_hair_type_keyboard(1, 6)
    )
    await UserState.HAIR_TYPE.set()

# ========== УХОД ЗА ТЕЛОМ ==========

@dp.message_handler(state=UserState.BODY_TYPE)
async def body_type_handler(message: types.Message, state: FSMContext):
    """Обработка выбора типа кожи тела"""
    text = message.text
    
    # Определяем тип по тексту кнопки
    if "Общий уход" in text:
        body_type = "general"
    elif "Сухая кожа" in text:
        body_type = "dry"
    elif "Чувствительная кожа" in text:
        body_type = "sensitive"
    elif "Борьба с целлюлитом" in text:
        body_type = "cellulite"
    else:
        await message.answer("Пожалуйста, выберите вариант из списка:", reply_markup=get_body_care_keyboard(1, 2))
        return
    
    # Сохраняем выбор
    user_storage.save_state(message.from_user.id, 'BODY_TYPE', {'body_type': body_type})
    
    # Формируем рекомендацию
    rec = BODY_CARE_RECOMMENDATIONS[body_type]
    
    response = f"""
{EMOJI['recommendation']} *Ваша персонализированная рекомендация*

{rec['title']}

*Рекомендуемые продукты:*
{chr(10).join(rec['products'])}

{LOCATIONS}

{DELIVERY_TEXT}

{EMOJI['restart']} *Для нового подбора нажмите «Начать заново»*
    """
    
    await message.answer(response, reply_markup=get_final_actions_keyboard())
    await UserState.BODY_RESULT.set()

# ========== УХОД ЗА ВОЛОСАМИ ==========

# Шаг 1: Тип волос
@dp.message_handler(state=UserState.HAIR_TYPE)
async def hair_type_handler(message: types.Message, state: FSMContext):
    """Обработка выбора типа волос"""
    text = message.text
    
    if "блондинка" in text.lower():
        hair_type = "blonde"
        next_step = "SCALP_TYPE"  # Пропускаем выбор цвета для блондинок
    elif "другой цвет" in text.lower():
        hair_type = "colored"
        next_step = "HAIR_PROBLEMS"
    elif "натуральные" in text.lower():
        hair_type = "natural"
        next_step = "HAIR_PROBLEMS"
    else:
        await message.answer("Пожалуйста, выберите вариант из списка:", reply_markup=get_hair_type_keyboard(1, 6))
        return
    
    # Сохраняем тип волос
    user_storage.save_state(message.from_user.id, 'HAIR_TYPE', {'hair_type': hair_type, 'next_step': next_step})
    
    # Показываем следующий шаг
    if next_step == "SCALP_TYPE":
        await message.answer(
            f"{EMOJI['step']} *Шаг 3 из 6: Кожа головы*\n\nЕсть ли у вас чувствительная кожа головы?",
            reply_markup=get_scalp_keyboard(3, 6)
        )
        await UserState.SCALP_TYPE.set()
    else:
        await message.answer(
            f"{EMOJI['step']} *Шаг 2 из 6: Проблемы волос*\n\nВыберите проблемы, которые вас беспокоят:",
            reply_markup=get_back_button()
        )
        await message.answer("Нажмите на проблемы, чтобы выбрать:", reply_markup=get_hair_problems_inline_keyboard())
        await UserState.HAIR_PROBLEMS.set()

# Обработка инлайн-кнопок для выбора проблем
@dp.callback_query_handler(lambda c: c.data.startswith('problem_'), state=UserState.HAIR_PROBLEMS)
async def process_problem_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора проблемы"""
    problem_id = callback_query.data.replace('problem_', '')
    user_id = callback_query.from_user.id
    
    # Получаем текущий список проблем
    current_problems = user_storage.get_problems(user_id)
    
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
    user_storage.save_problems(user_id, current_problems)
    
    # Обновляем клавиатуру
    await bot.edit_message_reply_markup(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=get_hair_problems_inline_keyboard(current_problems)
    )
    
    await bot.answer_callback_query(callback_query.id)

@dp.callback_query_handler(lambda c: c.data == 'problems_done', state=UserState.HAIR_PROBLEMS)
async def problems_done_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """Завершение выбора проблем"""
    user_id = callback_query.from_user.id
    problems = user_storage.get_problems(user_id)
    
    if not problems:
        await bot.answer_callback_query(callback_query.id, "Пожалуйста, выберите хотя бы одну проблему или 'Ничего из перечисленного'")
        return
    
    await bot.answer_callback_query(callback_query.id, "Выбор сохранён!")
    
    # Получаем сохранённый тип волос
    user_data = user_storage.get_state(user_id)
    hair_type = user_data['answers']['hair_type'] if user_data else 'colored'
    
    # Определяем следующий шаг
    if hair_type == 'blonde':
        next_state = UserState.SCALP_TYPE
        step_num = 3
        question = f"{EMOJI['step']} *Шаг {step_num} из 6: Кожа головы*\n\nЕсть ли у вас чувствительная кожа головы?"
        keyboard = get_scalp_keyboard(step_num, 6)
    else:
        next_state = UserState.SCALP_TYPE
        step_num = 3
        question = f"{EMOJI['step']} *Шаг {step_num} из 6: Кожа головы*\n\nЕсть ли у вас чувствительная кожа головы?"
        keyboard = get_scalp_keyboard(step_num, 6)
    
    await bot.send_message(callback_query.message.chat.id, question, reply_markup=keyboard)
    await next_state.set()

# Шаг 3: Кожа головы
@dp.message_handler(state=UserState.SCALP_TYPE)
async def scalp_type_handler(message: types.Message, state: FSMContext):
    """Обработка выбора типа кожи головы"""
    text = message.text.lower()
    
    if text in ['да', 'нет']:
        sensitive_scalp = (text == 'да')
        user_storage.save_state(message.from_user.id, 'SCALP_TYPE', {'sensitive_scalp': sensitive_scalp})
        
        # Получаем тип волос для определения следующего шага
        user_data = user_storage.get_state(message.from_user.id)
        hair_type = user_data['answers']['hair_type'] if user_data else 'colored'
        
        if hair_type == 'blonde':
            step_num = 4
            next_state = UserState.VOLUME_NEED
            question = f"{EMOJI['step']} *Шаг {step_num} из 6: Объём*\n\nХотите добавить средства для дополнительного объёма?"
            keyboard = get_volume_keyboard(step_num, 6)
        else:
            step_num = 4
            next_state = UserState.VOLUME_NEED
            question = f"{EMOJI['step']} *Шаг {step_num} из 6: Объём*\n\nХотите добавить средства для дополнительного объёма?"
            keyboard = get_volume_keyboard(step_num, 6)
        
        await message.answer(question, reply_markup=keyboard)
        await next_state.set()
    else:
        await message.answer("Пожалуйста, ответьте 'Да' или 'Нет':", reply_markup=get_scalp_keyboard(3, 6))

# Шаг 4: Объём
@dp.message_handler(state=UserState.VOLUME_NEED)
async def volume_handler(message: types.Message, state: FSMContext):
    """Обработка выбора объёма"""
    text = message.text.lower()
    
    if "хочу объём" in text:
        need_volume = True
    elif "не нужно" in text:
        need_volume = False
    else:
        await message.answer("Пожалуйста, выберите вариант из списка:", reply_markup=get_volume_keyboard(4, 6))
        return
    
    user_storage.save_state(message.from_user.id, 'VOLUME_NEED', {'need_volume': need_volume})
    
    # Получаем тип волос
    user_data = user_storage.get_state(message.from_user.id)
    hair_type = user_data['answers']['hair_type'] if user_data else 'colored'
    
    if hair_type == 'blonde':
        # Для блондинок сразу переходим к результату
        await show_hair_recommendation(message, state)
    else:
        # Для окрашенных - спрашиваем цвет
        step_num = 5
        await message.answer(
            f"{EMOJI['step']} *Шаг {step_num} из 6: Цвет волос*\n\nУточните, пожалуйста, ваш цвет волос?",
            reply_markup=get_hair_color_keyboard(step_num, 6)
        )
        await UserState.HAIR_COLOR.set()

# Шаг 5: Цвет волос (только для окрашенных не-блондинок)
@dp.message_handler(state=UserState.HAIR_COLOR)
async def hair_color_handler(message: types.Message, state: FSMContext):
    """Обработка выбора цвета волос"""
    text = message.text.lower()
    
    if text in ['шатенка', 'русая', 'рыжая', 'другой цвет']:
        user_storage.save_state(message.from_user.id, 'HAIR_COLOR', {'hair_color': text})
        await show_hair_recommendation(message, state)
    else:
        await message.answer("Пожалуйста, выберите вариант из списка:", reply_markup=get_hair_color_keyboard(5, 6))

# ========== ФОРМИРОВАНИЕ ИТОГОВОЙ РЕКОМЕНДАЦИИ ДЛЯ ВОЛОС ==========

async def show_hair_recommendation(message: types.Message, state: FSMContext):
    """Показать итоговую рекомендацию для волос"""
    user_id = message.from_user.id
    
    # Собираем все данные пользователя
    user_data = user_storage.get_state(user_id)
    problems = user_storage.get_problems(user_id)
    
    if not user_data:
        await message.answer("Произошла ошибка. Давайте начнём заново:", reply_markup=get_main_menu())
        await UserState.MAIN_MENU.set()
        return
    
    answers = {}
    for step_data in user_data.values():
        if isinstance(step_data, dict):
            answers.update(step_data)
    
    # Формируем рекомендацию
    response_parts = [f"{EMOJI['recommendation']} *Ваша персонализированная рекомендация*\n"]
    
    # 1. Базовый уход
    hair_type = answers.get('hair_type', 'colored')
    base_rec = HAIR_BASE_RECOMMENDATIONS.get(hair_type, HAIR_BASE_RECOMMENDATIONS['colored'])
    response_parts.append(f"\n{base_rec['title']}")
    response_parts.append(f"*Базовые продукты:*")
    response_parts.extend(base_rec['products'])
    
    # 2. Проблемы (кроме 'none')
    if problems and 'none' not in problems:
        response_parts.append(f"\n{EMOJI['problem']} *Решение проблем:*")
        for problem in problems:
            if problem in HAIR_PROBLEMS_RECOMMENDATIONS:
                rec = HAIR_PROBLEMS_RECOMMENDATIONS[problem]
                response_parts.append(f"\n{rec['title']}")
                response_parts.extend(rec['products'])
    
    # 3. Чувствительная кожа головы
    if answers.get('sensitive_scalp'):
        response_parts.append(f"\n{SENSITIVE_SCALP_RECOMMENDATION['title']}")
        response_parts.extend(SENSITIVE_SCALP_RECOMMENDATION['products'])
    
    # 4. Объём
    if answers.get('need_volume'):
        response_parts.append(f"\n{VOLUME_RECOMMENDATION['title']}")
        response_parts.extend(VOLUME_RECOMMENDATION['products'])
    
    # 5. Цветовые маски (только для окрашенных)
    if hair_type == 'colored':
        hair_color = answers.get('hair_color', '')
        if hair_color in COLOR_MASKS:
            color_rec = COLOR_MASKS[hair_color]
            response_parts.append(f"\n{color_rec['title']}")
            response_parts.extend(color_rec['products'])
    
    # 6. Точки продаж и доставка
    response_parts.append(f"\n{LOCATIONS}")
    response_parts.append(f"\n{DELIVERY_TEXT}")
    response_parts.append(f"\n{EMOJI['restart']} *Для нового подбора нажмите «Начать заново»*")
    
    # Отправляем рекомендацию
    await message.answer("\n".join(response_parts), reply_markup=get_final_actions_keyboard())
    await UserState.HAIR_RESULT.set()

# ========== ФИНАЛЬНЫЕ ДЕЙСТВИЯ ==========

@dp.message_handler(text=f"{EMOJI['location']} Точки продаж", state='*')
async def show_locations(message: types.Message):
    """Показать точки продаж"""
    await message.answer(LOCATIONS, reply_markup=get_final_actions_keyboard())

@dp.message_handler(text=f"{EMOJI['delivery']} Заказать доставку", state='*')
async def show_delivery(message: types.Message):
    """Показать информацию о доставке"""
    await message.answer(DELIVERY_TEXT, reply_markup=get_final_actions_keyboard())

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
    logger.info("Бот запущен!")
    if ADMIN_ID:
        await bot.send_message(ADMIN_ID, "🤖 Бот успешно запущен!")

async def on_shutdown(dp):
    """Действия при остановке бота"""
    logger.info("Бот остановлен!")
    await bot.close()

if __name__ == '__main__':
    # Запускаем поллинг (более стабильно для Render.com)
    executor.start_polling(
        dp, 
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )
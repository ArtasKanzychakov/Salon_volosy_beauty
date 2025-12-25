from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
import config

def main_kb():
    """Главная клавиатура"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="💇‍♀️ Волосы"))
    builder.add(KeyboardButton(text="🧴 Тело"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def back_to_start_kb():
    """Клавиатура для возврата в начало"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="👈 Назад"))
    return builder.as_markup(resize_keyboard=True)

def body_goal_kb():
    """Клавиатура для выбора цели ухода за телом"""
    builder = ReplyKeyboardBuilder()
    for goal in config.BODY_GOALS:
        builder.add(KeyboardButton(text=goal))
    builder.add(KeyboardButton(text="👈 Назад"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def hair_type_kb():
    """Клавиатура для выбора типа волос"""
    builder = ReplyKeyboardBuilder()
    for hair_type in config.HAIR_TYPES:
        builder.add(KeyboardButton(text=hair_type))
    builder.add(KeyboardButton(text="👈 Назад"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def hair_problems_kb(selected: list):
    """Клавиатура для выбора проблем волос (мультиселект)"""
    builder = ReplyKeyboardBuilder()
    
    for problem in config.HAIR_PROBLEMS:
        prefix = "✅
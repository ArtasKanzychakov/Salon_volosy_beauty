# admin_handlers.py - Обработчики админ-панели

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from admin_keyboards import *
from photo_storage import photo_storage, PHOTO_KEYS

# Состояния для админ-панели
class AdminState(StatesGroup):
    MAIN = State()
    UPLOAD = State()
    WAITING_PHOTO = State()
    DELETE_SELECT = State()
    DELETE_CONFIRM = State()

# Словарь для преобразования русских названий в ключи
NAME_TO_KEY = {v: k for k, v in PHOTO_KEYS.items()}

# Обратный словарь для упрощенных названий (для меню)
SIMPLIFIED_NAMES = {
    "Молочко для тела": "body_milk",
    "Гидрофильное масло": "hydrophilic_oil",
    "Крем суфле": "cream_body",
    "Скраб для тела": "body_scrub",
    "Гель для душа": "shower_gel",
    "Баттер для тела": "body_butter",
    "Гиалуроновая кислота": "hyaluronic_acid",
    "Биолипидный спрей": "biolipid_spray",
    "Сухое масло спрей": "dry_oil_spray",
    "Масло ELIXIR": "oil_elixir",
    "Молочко для волос": "hair_milk",
    "Масло концентрат": "oil_concentrate",
    "Флюид для волос": "hair_fluid",
    "Шампунь реконстракт": "reconstruct_shampoo",
    "Маска реконстракт": "reconstruct_mask",
    "Протеиновый крем": "protein_cream",
    "Шампунь для осветленных волос": "blonde_shampoo",
    "Кондиционер для осветленных волос": "blonde_conditioner",
    "Маска для осветленных волос": "blonde_mask",
    "Шампунь для окрашенных волос": "colored_shampoo",
    "Кондиционер для окрашенных волос": "colored_conditioner",
    "Маска для окрашенных волос": "colored_mask",
    "Оттеночная маска Холодный шоколад": "mask_cold_chocolate",
    "Оттеночная маска Медный": "mask_copper",
    "Оттеночная маска Розовая пудра": "mask_pink_powder",
    "Оттеночная маска Перламутр": "mask_mother_of_pearl",
    "Коллаж для блондинок": "blonde_general",
    "Коллаж: Ломкость волос": "blonde_lomkost",
    "Коллаж: Тусклость": "hair_milk_concentrate",
    "Коллаж: Пушистость": "fluid_protein_elixir",
    "Коллаж: Тонкие волосы": "thin_hair_care",
    "
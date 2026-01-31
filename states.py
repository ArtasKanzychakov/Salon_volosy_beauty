"""
STATES.PY - Состояния FSM для бота
"""

from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    """Состояния пользователя"""
    CHOOSING_CATEGORY = State()
    BODY_CHOOSING_GOAL = State()
    HAIR_CHOOSING_TYPE = State()
    HAIR_CHOOSING_PROBLEMS = State()
    HAIR_CHOOSING_SCALP = State()
    HAIR_CHOOSING_VOLUME = State()
    HAIR_CHOOSING_COLOR = State()

class AdminState(StatesGroup):
    """Состояния админ-панели"""
    WAITING_PASSWORD = State()
    ADMIN_MAIN_MENU = State()
    ADMIN_PHOTOS_MENU = State()
    ADMIN_BULK_UPLOAD = State()
    ADMIN_WAITING_BULK_PHOTO = State()
    ADMIN_CONFIRM_RESET = State()
    
    # Для массовой загрузки
    ADMIN_BULK_CATEGORY = State()
    ADMIN_BULK_SUBCATEGORY = State()
    ADMIN_BULK_PRODUCT_LIST = State()

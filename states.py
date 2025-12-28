"""
STATES.PY - Состояния FSM для бота
Единая система именования состояний
"""

from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    """Состояния пользователя"""
    # Основные состояния
    MAIN_MENU = State()              # Главное меню
    CHOOSING_CATEGORY = State()      # Выбор категории (волосы/тело)
    
    # Состояния для категории "Тело"
    BODY_CHOOSING_GOAL = State()     # Выбор цели для тела
    
    # Состояния для категории "Волосы"
    HAIR_CHOOSING_TYPE = State()     # Выбор типа волос
    HAIR_CHOOSING_PROBLEMS = State() # Выбор проблем (мультивыбор)
    HAIR_CHOOSING_SCALP = State()    # Выбор типа кожи головы
    HAIR_CHOOSING_VOLUME = State()   # Выбор объема
    HAIR_CHOOSING_COLOR = State()    # Выбор цвета (для окрашенных)
    
    # Финальное состояние
    SHOWING_RESULT = State()         # Показ результата

class AdminState(StatesGroup):
    """Состояния админ-панели"""
    AWAITING_PASSWORD = State()      # Ожидание пароля
    ADMIN_MAIN_MENU = State()        # Главное меню админки
    ADMIN_CHOOSING_CATEGORY = State() # Выбор категории для загрузки
    ADMIN_CHOOSING_PRODUCT = State()  # Выбор продукта
    ADMIN_AWAITING_PHOTO = State()    # Ожидание фото
from aiogram.dispatcher.filters.state import State, StatesGroup

class UserState(StatesGroup):
    # Общие состояния
    MAIN_MENU = State()
    
    # Уход за телом
    BODY_CARE = State()
    BODY_TYPE = State()
    BODY_RESULT = State()
    
    # Уход за волосами
    HAIR_CARE = State()
    HAIR_TYPE = State()
    HAIR_PROBLEMS = State()
    SCALP_TYPE = State()
    VOLUME_NEED = State()
    HAIR_COLOR = State()
    HAIR_RESULT = State()
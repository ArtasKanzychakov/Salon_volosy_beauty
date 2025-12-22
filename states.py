from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    # Главное меню
    MAIN_MENU = State()
    
    # Ветка "Тело"
    BODY_CHOICE = State()
    
    # Ветка "Волосы"
    HAIR_TYPE = State()          # Тип волос
    HAIR_PROBLEMS = State()      # Проблемы (мультивыбор)
    HAIR_SCALP = State()         # Чувствительность кожи головы
    HAIR_VOLUME = State()        # Нужен ли объем
    HAIR_COLOR = State()         # Цвет волос (только для окрашенных)
    HAIR_RESULT = State()        # Показ результата
    
    # Финальное состояние
    FINAL = State()

class AdminState(StatesGroup):
    MAIN = State()
    UPLOAD = State()
    WAITING_PHOTO = State()
    DELETE_SELECT = State()
    DELETE_CONFIRM = State()
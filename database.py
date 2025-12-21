# database.py - Простое хранилище данных пользователя
user_data = {}

def save_user_data(user_id, key, value):
    """Сохранить данные пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id][key] = value

def get_user_data(user_id, key=None):
    """Получить данные пользователя"""
    if user_id not in user_data:
        return None if key else {}
    if key:
        return user_data[user_id].get(key)
    return user_data[user_id]

def delete_user_data(user_id):
    """Удалить все данные пользователя"""
    if user_id in user_data:
        del user_data[user_id]

def clear_user_data(user_id):
    """Алиас для delete_user_data (для обратной совместимости)"""
    delete_user_data(user_id)

# Функции для мультивыбора проблем
def add_selected_problem(user_id, problem):
    """Добавить проблему в список выбранных"""
    if user_id not in user_data:
        user_data[user_id] = {}
    if "selected_problems" not in user_data[user_id]:
        user_data[user_id]["selected_problems"] = []

    if problem not in user_data[user_id]["selected_problems"]:
        user_data[user_id]["selected_problems"].append(problem)

def get_selected_problems(user_id):
    """Получить список выбранных проблем"""
    return user_data.get(user_id, {}).get("selected_problems", [])

def clear_selected_problems(user_id):
    """Очистить список выбранных проблем"""
    if user_id in user_data and "selected_problems" in user_data[user_id]:
        user_data[user_id]["selected_problems"] = []
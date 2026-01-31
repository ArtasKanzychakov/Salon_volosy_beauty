"""
USER_STORAGE.PY - Хранилище данных пользователей (в памяти)
На Render Free данные теряются при рестарте, но это нормально для текущей сессии
"""

from typing import Dict, Any

# Хранилище в памяти (теряется при рестарте сервера)
user_data = {}

def save_user_data(user_id: int, key: str, value: Any):
    """Сохранить данные пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id][key] = value

def get_user_data(user_id: int, key: str = None) -> Any:
    """Получить данные пользователя"""
    if user_id not in user_data:
        return None if key else {}
    if key:
        return user_data[user_id].get(key)
    return user_data[user_id]

def delete_user_data(user_id: int):
    """Удалить все данные пользователя"""
    if user_id in user_data:
        del user_data[user_id]

def add_selected_problem(user_id: int, problem: str):
    """Добавить проблему в список выбранных"""
    if user_id not in user_data:
        user_data[user_id] = {}
    if "selected_problems" not in user_data[user_id]:
        user_data[user_id]["selected_problems"] = []

    if problem not in user_data[user_id]["selected_problems"]:
        user_data[user_id]["selected_problems"].append(problem)

def remove_selected_problem(user_id: int, problem: str):
    """Удалить проблему из списка"""
    if user_id in user_data and "selected_problems" in user_data[user_id]:
        if problem in user_data[user_id]["selected_problems"]:
            user_data[user_id]["selected_problems"].remove(problem)

def get_selected_problems(user_id: int) -> list:
    """Получить список выбранных проблем"""
    if user_id not in user_data:
        return []
    return user_data[user_id].get("selected_problems", [])

def clear_selected_problems(user_id: int):
    """Очистить список выбранных проблем"""
    if user_id in user_data and "selected_problems" in user_data[user_id]:
        user_data[user_id]["selected_problems"] = []

def get_user_data_value(user_id: int, key: str, default: Any = None) -> Any:
    """Получить значение с дефолтом"""
    return get_user_data(user_id, key) or default

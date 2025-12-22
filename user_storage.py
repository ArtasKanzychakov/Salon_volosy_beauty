# Простое хранилище данных пользователя
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

# Функции для мультивыбора проблем
def add_selected_problem(user_id, problem):
    """Добавить проблему в список выбранных"""
    if user_id not in user_data:
        user_data[user_id] = {}
    if "selected_problems" not in user_data[user_id]:
        user_data[user_id]["selected_problems"] = []
    
    # Если выбрано "Ничего из перечисленного", очищаем список
    if problem == "Ничего из перечисленного, только общий уход":
        user_data[user_id]["selected_problems"] = ["Общий уход"]
        return
    
    # Убираем "Общий уход", если выбирается конкретная проблема
    if "Общий уход" in user_data[user_id]["selected_problems"] and problem != "Общий уход":
        user_data[user_id]["selected_problems"].remove("Общий уход")
    
    if problem not in user_data[user_id]["selected_problems"]:
        user_data[user_id]["selected_problems"].append(problem)

def remove_selected_problem(user_id, problem):
    """Удалить проблему из списка"""
    if user_id in user_data and "selected_problems" in user_data[user_id]:
        if problem in user_data[user_id]["selected_problems"]:
            user_data[user_id]["selected_problems"].remove(problem)
        
        # Если список пустой, добавляем "Общий уход"
        if not user_data[user_id]["selected_problems"]:
            user_data[user_id]["selected_problems"] = ["Общий уход"]

def get_selected_problems(user_id):
    """Получить список выбранных проблем"""
    problems = user_data.get(user_id, {}).get("selected_problems", [])
    
    # Если список пустой, значит только общий уход
    if not problems:
        return ["Общий уход"]
    
    # Удаляем дубликаты
    seen = set()
    unique_problems = []
    for problem in problems:
        if problem not in seen:
            seen.add(problem)
            unique_problems.append(problem)
    
    return unique_problems

def clear_selected_problems(user_id):
    """Очистить список выбранных проблем"""
    if user_id in user_data and "selected_problems" in user_data[user_id]:
        user_data[user_id]["selected_problems"] = []
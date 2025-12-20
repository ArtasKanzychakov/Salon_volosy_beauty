# Простое хранилище данных пользователя
user_data = {}

def save_user_data(user_id, key, value):
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id][key] = value

def get_user_data(user_id, key=None):
    if user_id not in user_data:
        return None if key else {}
    if key:
        return user_data[user_id].get(key)
    return user_data[user_id]

def clear_user_data(user_id):
    if user_id in user_data:
        del user_data[user_id]
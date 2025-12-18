"""Простое хранилище данных в оперативной памяти"""
storage = {}

def save_user_data(user_id, key, value):
    if user_id not in storage:
        storage[user_id] = {}
    storage[user_id][key] = value

def get_user_data(user_id, key=None):
    user_data = storage.get(user_id, {})
    if key:
        return user_data.get(key)
    return user_data

def delete_user_data(user_id):
    if user_id in storage:
        del storage[user_id]
import json
import time

class MemoryStorage:
    def __init__(self):
        self.data = {}
        self.problems_data = {}
    
    def save_state(self, user_id, state, answers):
        """Сохранить состояние пользователя"""
        self.data[user_id] = {
            'state': state,
            'answers': answers,
            'timestamp': time.time()
        }
    
    def get_state(self, user_id):
        """Получить состояние пользователя"""
        return self.data.get(user_id)
    
    def delete_state(self, user_id):
        """Удалить состояние пользователя"""
        if user_id in self.data:
            del self.data[user_id]
    
    def save_problems(self, user_id, problems):
        """Сохранить выбранные проблемы"""
        self.problems_data[user_id] = problems
    
    def get_problems(self, user_id):
        """Получить выбранные проблемы"""
        return self.problems_data.get(user_id, [])
    
    def delete_problems(self, user_id):
        """Удалить выбранные проблемы"""
        if user_id in self.problems_data:
            del self.problems_data[user_id]
    
    def cleanup_old(self, max_age_hours=24):
        """Очистить старые данные"""
        current_time = time.time()
        expired_users = []
        
        for user_id, data in self.data.items():
            if current_time - data['timestamp'] > max_age_hours * 3600:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self.delete_state(user_id)
            self.delete_problems(user_id)
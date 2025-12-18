import time

class MemoryStorage:
    def __init__(self):
        self.data = {}
    
    def save(self, user_id, key, value):
        if user_id not in self.data:
            self.data[user_id] = {}
        self.data[user_id][key] = value
    
    def get(self, user_id, key=None):
        if user_id not in self.data:
            return None
        if key:
            return self.data[user_id].get(key)
        return self.data[user_id]
    
    def delete(self, user_id):
        if user_id in self.data:
            del self.data[user_id]
    
    def clear(self):
        self.data.clear()

storage = MemoryStorage()
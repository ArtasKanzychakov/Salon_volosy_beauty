"""
USER_STORAGE.PY - Хранилище данных пользователей
С улучшенной системой очистки и мониторингом
"""

import asyncio
import time
from typing import Dict, Any, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class UserDataStorage:
    """Асинхронное хранилище данных пользователей с TTL"""
    
    def __init__(self, ttl_hours: int = 24):
        """
        :param ttl_hours: Время жизни данных в часах
        """
        self._storage = {}
        self._timestamps = {}
        self.ttl_seconds = ttl_hours * 3600
        self._cleanup_task = None
        logger.info(f"Инициализировано хранилище пользователей (TTL: {ttl_hours}ч)")
    
    async def start_cleanup(self, interval_minutes: int = 30):
        """Запуск периодической очистки устаревших данных"""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(interval_minutes * 60)
                await self._cleanup_old_data()
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(f"Запущена очистка данных каждые {interval_minutes} мин")
    
    async def stop_cleanup(self):
        """Остановка очистки"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Очистка данных остановлена")
    
    async def _cleanup_old_data(self):
        """Очистка устаревших данных"""
        current_time = time.time()
        to_delete = []
        
        for user_id, timestamp in self._timestamps.items():
            if current_time - timestamp > self.ttl_seconds:
                to_delete.append(user_id)
        
        for user_id in to_delete:
            self._storage.pop(user_id, None)
            self._timestamps.pop(user_id, None)
        
        if to_delete:
            logger.info(f"Очищены данные {len(to_delete)} пользователей")
    
    def get_data(self, user_id: int) -> Dict[str, Any]:
        """Получить данные пользователя"""
        return self._storage.get(user_id, {}).copy()
    
    def update_data(self, user_id: int, data: Dict[str, Any]) -> None:
        """Обновить данные пользователя"""
        if user_id not in self._storage:
            self._storage[user_id] = {}
        
        self._storage[user_id].update(data)
        self._timestamps[user_id] = time.time()
        logger.debug(f"Обновлены данные пользователя {user_id}")
    
    def clear_data(self, user_id: int) -> None:
        """Очистить данные пользователя"""
        self._storage.pop(user_id, None)
        self._timestamps.pop(user_id, None)
        logger.debug(f"Очищены данные пользователя {user_id}")
    
    def get_all_users(self) -> list:
        """Получить список всех пользователей"""
        return list(self._storage.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика хранилища"""
        return {
            "total_users": len(self._storage),
            "total_entries": sum(len(data) for data in self._storage.values()),
            "oldest_timestamp": min(self._timestamps.values()) if self._timestamps else None,
            "newest_timestamp": max(self._timestamps.values()) if self._timestamps else None
        }

# Глобальный экземпляр хранилища
user_data_storage = UserDataStorage(ttl_hours=24)

# Функции для обратной совместимости
async def init_user_storage():
    """Инициализация хранилища с запуском очистки"""
    await user_data_storage.start_cleanup()
    return user_data_storage
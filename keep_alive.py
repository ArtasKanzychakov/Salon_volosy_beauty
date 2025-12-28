"""
KEEP_ALIVE.PY - Система поддержания активности и предотвращения клонов
"""

import os
import asyncio
import aiohttp
import logging
import signal
import sys
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class SingletonMeta(type):
    """Мета-класс для реализации Singleton"""
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class KeepAliveSystem(metaclass=SingletonMeta):
    """Система поддержания активности с предотвращением дублирования"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.environ.get("RENDER_URL", "")
        self.health_check_url = f"{self.base_url}/health" if self.base_url else None
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.instance_id = os.environ.get("RENDER_INSTANCE_ID", "local")
        
        logger.info(f"🚀 KeepAliveSystem инициализирован (ID: {self.instance_id})")
    
    async def start(self, ping_interval: int = 300):
        """Запуск системы keep-alive"""
        if self.is_running:
            logger.warning("Keep-alive уже запущен")
            return
        
        self.is_running = True
        
        # Создаем HTTP-сессию
        self.session = aiohttp.ClientSession()
        
        # Регистрируем обработчик сигналов
        self._register_signal_handlers()
        
        # Запускаем задачу
        self.task = asyncio.create_task(self._keep_alive_loop(ping_interval))
        logger.info(f"Keep-alive запущен (интервал: {ping_interval} сек)")
    
    async def stop(self):
        """Остановка системы keep-alive"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        if self.session:
            await self.session.close()
        
        logger.info("Keep-alive остановлен")
    
    def _register_signal_handlers(self):
        """Регистрация обработчиков сигналов"""
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов"""
        logger.info(f"Получен сигнал {signum}, останавливаем keep-alive...")
        asyncio.create_task(self.stop())
    
    async def _keep_alive_loop(self, interval: int):
        """Основной цикл отправки ping-запросов"""
        while self.is_running:
            try:
                await self._send_ping()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в keep-alive цикле: {e}")
                await asyncio.sleep(interval)
    
    async def _send_ping(self):
        """Отправка ping-запроса"""
        if not self.health_check_url:
            logger.warning("URL для health check не указан")
            return
        
        try:
            async with self.session.get(self.health_check_url, timeout=10) as response:
                if response.status == 200:
                    logger.debug(f"✅ Health check успешен: {self.health_check_url}")
                else:
                    logger.warning(f"⚠️ Health check неожиданный статус: {response.status}")
        except aiohttp.ClientError as e:
            logger.error(f"❌ Ошибка health check: {e}")
        except asyncio.TimeoutError:
            logger.warning("⚠️ Health check timeout")
    
    async def check_instance_uniqueness(self) -> bool:
        """Проверка уникальности экземпляра (предотвращение клонов)"""
        # На Render каждый экземпляр имеет уникальный ID
        if self.instance_id != "local":
            logger.info(f"Экземпляр уникален (ID: {self.instance_id})")
            return True
        
        # Для локального запуска проверяем PID файл
        pid_file = "/tmp/bot_instance.pid"
        
        try:
            if os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    old_pid = int(f.read().strip())
                
                # Проверяем, жив ли процесс с таким PID
                try:
                    os.kill(old_pid, 0)
                    logger.warning(f"⚠️ Найден запущенный экземпляр с PID {old_pid}")
                    return False
                except OSError:
                    # Процесс не существует, можем продолжить
                    pass
            
            # Записываем свой PID
            with open(pid_file, 'w') as f:
                f.write(str(os.getpid()))
            
            logger.info(f"Экземпляр зарегистрирован с PID {os.getpid()}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка проверки уникальности экземпляра: {e}")
            return True
    
    async def cleanup_pid_file(self):
        """Очистка PID файла при завершении"""
        pid_file = "/tmp/bot_instance.pid"
        try:
            if os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    if int(f.read().strip()) == os.getpid():
                        os.remove(pid_file)
                        logger.info("PID файл очищен")
        except Exception as e:
            logger.error(f"Ошибка очистки PID файла: {e}")

# Глобальный экземпляр
keep_alive_system = KeepAliveSystem()

# Функции для импорта
async def keep_alive_start():
    """Запуск keep-alive системы"""
    # Проверяем уникальность экземпляра
    if not await keep_alive_system.check_instance_uniqueness():
        logger.error("⚠️ Обнаружен другой запущенный экземпляр. Завершаемся.")
        sys.exit(1)
    
    await keep_alive_system.start()

async def keep_alive_stop():
    """Остановка keep-alive системы"""
    await keep_alive_system.cleanup_pid_file()
    await keep_alive_system.stop()
# keep_alive.py - Система авто-пинга для поддержания активности бота
import os
import time
import threading
import urllib.request
import urllib.error
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class KeepAlive:
    """
    Класс для периодического пинга сервиса, чтобы предотвратить засыпание на Render
    Render бесплатный тариф засыпает после 15 минут бездействия
    """
    
    def __init__(self, url=None, interval=480):
        """
        Инициализация системы keep-alive
        
        Args:
            url (str): URL вашего сервиса на Render
            interval (int): Интервал пинга в секундах (по умолчанию 480 = 8 минут)
        """
        self.url = url or os.environ.get("RENDER_URL", "https://salon-volosy-beauty10.onrender.com")
        self.interval = interval  # Интервал в секундах
        self.is_running = False
        self.thread = None
        
        # Убедимся, что URL имеет правильный формат
        if not self.url.startswith(('http://', 'https://')):
            self.url = f"https://{self.url}"
        
        logger.info(f"🔧 KeepAlive инициализирован для URL: {self.url}")
    
    def _ping_service(self):
        """Выполнить один пинг сервиса"""
        try:
            # Пробуем несколько эндпоинтов
            endpoints = ['/health', '/ping', '/']
            
            for endpoint in endpoints:
                try:
                    ping_url = f"{self.url.rstrip('/')}{endpoint}"
                    req = urllib.request.Request(
                        ping_url,
                        headers={'User-Agent': 'KeepAlive-Ping/1.0'}
                    )
                    
                    with urllib.request.urlopen(req, timeout=15) as response:
                        status = response.getcode()
                        current_time = datetime.now().strftime("%H:%M:%S")
                        
                        if status == 200:
                            logger.info(f"✅ [{current_time}] Ping успешен: {ping_url} (Status: {status})")
                            return True
                        else:
                            logger.warning(f"⚠️ [{current_time}] Ping неудачен: {ping_url} (Status: {status})")
                            
                except urllib.error.URLError as e:
                    logger.debug(f"⚠️ Эндпоинт {endpoint} не доступен: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"⚠️ Ошибка при пинге {endpoint}: {e}")
                    continue
            
            # Если ни один эндпоинт не сработал
            logger.error(f"❌ Все эндпоинты не доступны")
            return False
            
        except Exception as e:
            current_time = datetime.now().strftime("%H:%M:%S")
            logger.error(f"❌ [{current_time}] Критическая ошибка пинга: {e}")
            return False
    
    def _worker(self):
        """Фоновый рабочий процесс для пинга"""
        logger.info(f"🚀 Keep-alive worker запущен. Интервал: {self.interval} сек.")
        
        while self.is_running:
            try:
                self._ping_service()
                
                # Считаем время до следующего пинга
                for i in range(self.interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ Ошибка в worker: {e}")
                # Ждем 30 секунд перед повторной попыткой при ошибке
                time.sleep(30)
    
    def start(self):
        """Запустить систему keep-alive"""
        if self.is_running:
            logger.warning("⚠️ Keep-alive уже запущен")
            return
        
        self.is_running = True
        
        # Создаем и запускаем поток
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        
        logger.info(f"🚀 Keep-alive система запущена. Пинг каждые {self.interval//60} минут.")
    
    def stop(self):
        """Остановить систему keep-alive"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        logger.info("🛑 Keep-alive система остановлена.")
    
    def get_status(self):
        """Получить статус системы"""
        return {
            "is_running": self.is_running,
            "url": self.url,
            "interval": self.interval,
            "thread_alive": self.thread.is_alive() if self.thread else False
        }


# Глобальный экземпляр для легкого доступа
_keep_alive_instance = None

def start_keep_alive(url=None, interval=480):
    """Запустить keep-alive систему (глобальная функция)"""
    global _keep_alive_instance
    
    if _keep_alive_instance is None:
        _keep_alive_instance = KeepAlive(url=url, interval=interval)
    
    _keep_alive_instance.start()
    return _keep_alive_instance

def stop_keep_alive():
    """Остановить keep-alive систему"""
    global _keep_alive_instance
    if _keep_alive_instance:
        _keep_alive_instance.stop()

def get_keep_alive_status():
    """Получить статус keep-alive системы"""
    global _keep_alive_instance
    if _keep_alive_instance:
        return _keep_alive_instance.get_status()
    return {"is_running": False}
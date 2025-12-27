import threading
import time
import requests
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

# Настройка логгера
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Обработчик для health checks"""
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Отключаем стандартное логирование запросов
        pass

def start_health_server(port=10000):
    """Запуск HTTP сервера для health checks"""
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    
    def run_server():
        logger.info(f"🌐 HTTP-сервер запущен на порту {port}")
        server.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return server

def keep_alive_worker(url, interval=480):
    """Рабочий поток для keep-alive"""
    logger.info(f"🚀 Keep-alive worker запущен. Интервал: {interval} сек.")
    
    while True:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                logger.info(f"✅ Keep-alive ping успешен: {url}")
            else:
                logger.warning(f"⚠️ Keep-alive ping неожиданный статус: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Keep-alive ping ошибка: {e}")
        
        time.sleep(interval)

class KeepAliveSystem:
    """Система поддержания активности бота на Render"""
    
    def __init__(self, base_url=None, health_port=10000):
        self.base_url = base_url or "https://salon-volosy-beauty11.onrender.com"
        self.health_port = health_port
        self.health_server = None
        self.keep_alive_thread = None
        
        logger.info(f"🔧 KeepAlive инициализирован для URL: {self.base_url}")
    
    def start(self):
        """Запуск всей системы keep-alive"""
        # Запускаем health check сервер
        self.health_server = start_health_server(self.health_port)
        
        # Запускаем keep-alive ping поток
        self.keep_alive_thread = threading.Thread(
            target=keep_alive_worker,
            args=(self.base_url, 480),
            daemon=True
        )
        self.keep_alive_thread.start()
        
        logger.info("🚀 Keep-alive система запущена. Пинг каждые 8 минут.")
    
    def stop(self):
        """Остановка системы keep-alive"""
        if self.health_server:
            self.health_server.shutdown()
            logger.info("🛑 Keep-alive система остановлена.")

# Создаем глобальный экземпляр
_keep_alive_instance = KeepAliveSystem()

# Функции для импорта
def keep_alive_start():
    """Запуск keep-alive системы"""
    _keep_alive_instance.start()

def keep_alive_stop():
    """Остановка keep-alive системы"""
    _keep_alive_instance.stop()

# Для совместимости с существующим кодом
if __name__ == "__main__":
    keep_alive_start()
    
    try:
        # Бесконечный цикл для тестирования
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        keep_alive_stop()
        print("Keep-alive остановлен")
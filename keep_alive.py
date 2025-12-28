import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class HealthHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP запросов для health check"""
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
        # Отключаем стандартное логирование запросов в консоль
        pass

def run_health_server():
    """Запуск HTTP сервера для health check"""
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"🌐 Health check сервер запущен на порту {port}")
    server.serve_forever()

def keep_alive():
    """Запуск health check сервера в отдельном потоке"""
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    print("🔔 Health check система активирована")

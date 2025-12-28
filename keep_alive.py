"""
KEEP_ALIVE.PY - Система health check для Render
"""

import os
import logging
from aiohttp import web

logger = logging.getLogger(__name__)

async def health_check(request):
    """Health check endpoint для Render"""
    return web.Response(text='OK')

async def start_health_server():
    """Запуск HTTP сервера для health checks"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    
    # Получаем порт из окружения (Render сам задает)
    port = int(os.environ.get("PORT", 10000))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🌐 Health server запущен на порту {port}")
    return runner

async def stop_health_server(runner):
    """Остановка health сервера"""
    await runner.cleanup()
    logger.info("🛑 Health server остановлен")
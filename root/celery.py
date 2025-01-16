from __future__ import absolute_import, unicode_literals

import asyncio
import os
from datetime import timedelta

from celery import Celery

# default Django settings module for the 'celery' program.
from proxy_checker import ProxyChecker

from proxy.models import Proxy

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')

app = Celery('root')  # project name as the Celery app name

# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Обновление конфигурации брокера
app.conf.broker_transport_options = {
    "visibility_timeout": 3600,  # Тайм-аут задач
    "socket_timeout": 30,  # Тайм-аут подключения
    "retry_on_timeout": True,  # Переподключение при ошибках
    "health_check_interval": 25,  # Интервал проверки состояния брокера
}

app.conf.beat_schedule = {
    "proxies": {
        "proxies": 'proxy.tasks',
        "schedule": timedelta(seconds=15),
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")

@app.task
def check_proxy_health():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_check_proxy_help())


async def async_check_proxy_help():
    checker = ProxyChecker()
    proxies = Proxy.objects.all()

    for proxy in proxies:
        response = checker.check_proxy(f'{proxy.host}:{proxy.port}')
        if not response:
            proxy.is_active = False

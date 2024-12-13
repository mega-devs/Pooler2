from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Установка переменных окружения
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")

# Создание приложения Celery
app = Celery("pooler_v2")

# Загрузка конфигурации из Django
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматическое обнаружение задач
app.autodiscover_tasks()

# Обновление конфигурации брокера
app.conf.broker_transport_options = {
    "visibility_timeout": 3600,  # Тайм-аут задач
    "socket_timeout": 30,  # Тайм-аут подключения
    "retry_on_timeout": True,  # Переподключение при ошибках
    "health_check_interval": 25,  # Интервал проверки состояния брокера
}

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
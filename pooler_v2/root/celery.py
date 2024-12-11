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

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
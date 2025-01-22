from __future__ import absolute_import, unicode_literals

import os
from datetime import timedelta

from celery import Celery


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
        "task": 'proxy.tasks.check_proxy_health',
        "schedule": timedelta(seconds=300),
    },
    'backup': {
        'task': 'proxy.tasks.backup_task',
        "schedule": timedelta(hours=12),
    },
    'check_imap_emails_from_db': {
        "task": 'pooler.tasks.check_imap_emails_from_db',
        "schedule": timedelta(seconds=15),
    },
    'check_smtp_emails_from_db': {
        "task": 'pooler.tasks.check_smtp_emails_from_db',
        "schedule": timedelta(seconds=15),
    }
}


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


from django.core.management.base import BaseCommand
from django.conf import settings
import random
from datetime import datetime, timedelta
import aiofiles
import asyncio

# for testing while integrating with front, some fake data
class Command(BaseCommand):
    help = 'Generates test logs for all log types'

    async def generate_logs(self):
        servers = ['smtp.gmail.com', 'smtp.yahoo.com', 'smtp.outlook.com']
        users = ['test1@gmail.com', 'test2@yahoo.com', 'test3@outlook.com']
        ports = ['587', '465', '25']
        responses = ['250 OK', '550 Failed', '421 Service not available']
        proxy_ports = ['1080', '8080', '3128']
        urls = ['http://example1.com', 'http://example2.com', 'http://example3.com']
        file_sizes = ['1.2MB', '650KB', '2.1GB']
        line_counts = ['1000', '2500', '5000']
        statuses = ['CLEANED', 'DOWNLOADED', 'FILTERED', 'CHECKED']

        async with aiofiles.open(settings.LOG_FILES['smtp'], 'w') as f:
            for i in range(20):
                color = random.choice(['GREEN', 'RED'])
                log_entry = f"{color}|Thread-{i}|{datetime.now()}|{random.choice(servers)}|{random.choice(users)}|{random.choice(ports)}|{random.choice(responses)}\n"
                await f.write(log_entry)

        async with aiofiles.open(settings.LOG_FILES['imap'], 'w') as f:
            for i in range(20):
                color = random.choice(['GREEN', 'RED'])
                log_entry = f"{color}|Thread-{i}|{datetime.now()}|{random.choice(servers)}|{random.choice(users)}|{random.choice(ports)}|{'VALID' if color == 'GREEN' else 'INVALID'}\n"
                await f.write(log_entry)

        async with aiofiles.open(settings.LOG_FILES['socks'], 'w') as f:
            for i in range(20):
                log_entry = f"Thread-{i}|{datetime.now()}|{random.choice(proxy_ports)}|{'SUCCESS' if random.random() > 0.5 else 'FAILED'}\n"
                await f.write(log_entry)

        async with aiofiles.open(settings.LOG_FILES['url_fetch'], 'w') as f:
            for i in range(20):
                log_entry = f"{datetime.now()}|file_{i}.txt|{random.choice(urls)}|{random.choice(file_sizes)}|{random.choice(line_counts)}|{random.choice(statuses)}\n"
                await f.write(log_entry)

        async with aiofiles.open(settings.LOG_FILES['telegram_fetch'], 'w') as f:
            for i in range(20):
                log_entry = f"{datetime.now()}|tg_file_{i}.txt|{random.choice(urls)}|{random.choice(file_sizes)}|{random.choice(line_counts)}|{random.choice(statuses)}\n"
                await f.write(log_entry)

    def handle(self, *args, **kwargs):
        asyncio.run(self.generate_logs())
        self.stdout.write(self.style.SUCCESS('Successfully generated test logs'))

import asyncio
import datetime
import os

import aiofiles
from celery import shared_task
from redis.exceptions import ConnectionError, ResponseError

from pooler.utils import LogFormatter
from root import settings

from .models import UploadedFile, URLFetcher
from .service import handle_archive, process_uploaded_files
from root.logger import getLogger

logger = getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, ResponseError),
    retry_backoff=True,
    retry_kwargs={'max_retries': 5}
)
def handle_archive_task(self, file_path, save_path):
    """Handles archive extraction."""
    try:
        handle_archive(file_path)
        logger.info(f"Файл {file_path} успешно распакован в {save_path}.")
    except Exception as e:
        logger.error(f"Ошибка распаковки архива {file_path}: {e}")
        raise e


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, ResponseError),
    retry_backoff=True,
    retry_kwargs={'max_retries': 5}
)
def process_uploaded_files_task(self, base_upload_dir, uploaded_file_id):
    """Processes uploaded files."""
    try:
        uploaded_file = UploadedFile.objects.get(id=uploaded_file_id)
        process_uploaded_files(base_upload_dir, uploaded_file)
        logger.info(f"Файлы из {base_upload_dir} успешно обработаны.")
    except Exception as e:
        logger.error(f"Ошибка обработки файлов из {base_upload_dir}: {e}")
        raise e


@shared_task(bind=True)
def fetch_files_from_url(self):
    """Fetches files from URLs and logs details."""
    try:
        thread_num = self.request.id
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        urls = URLFetcher.objects.all()
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        log_entries = []
        for url in urls:
            dir_path = os.path.join(project_root, url.link)

            # Ensure directory exists
            if not os.path.exists(dir_path):
                logger.warning(f"Directory not found: {dir_path}")
                continue

            total_files = 0
            total_lines = 0
            total_size = 0

            for filename in os.listdir(dir_path):
                file_full_path = os.path.join(dir_path, filename)
                status = "INVALID"
                size = 0
                lines = 0
                try:
                    if os.path.isfile(file_full_path):
                        total_files += 1
                        size = os.path.getsize(file_full_path)
                        total_size += size

                        with open(file_full_path, 'r', encoding='utf-8') as file:
                            lines = file.readlines()
                            total_lines += len(lines)
                            status = "VALID"
                except Exception as e:
                    logger.error(f"Error reading file {file_full_path}: {e}")
                    status = "ERROR"

                log_entry = LogFormatter.format_url_fetch_log(
                    thread_num,
                    timestamp, 
                    filename,
                    url.link,
                    size,
                    len(lines),
                    status
                )

                log_entries.append(log_entry)

            # Update database
            url.total_files_fetched = total_files
            url.total_lines_added = total_lines
            url.total_size_fetched = total_size
            url.last_time_fetched = datetime.datetime.now()
            url.success = True
            url.save()

        # Write logs asynchronously
        async def write_logs():
            async with aiofiles.open(settings.LOG_FILES['smtp'], 'a') as f:
                await f.write("\n".join(log_entries) + '\n')

        asyncio.run(write_logs())

    except Exception as e:
        logger.error(f"Error in fetch_files_from_url: {e}")
        raise e

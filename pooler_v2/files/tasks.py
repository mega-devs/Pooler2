from celery import shared_task
import logging
from .models import UploadedFile
from .service import handle_archive, process_uploaded_files

logger = logging.getLogger(__name__)


@shared_task
def async_handle_archive(file_path, save_path):
    try:
        handle_archive(file_path, save_path)
        logger.info(f"Файл {file_path} успешно распакован в {save_path}.")
    except Exception as e:
        logger.error(f"Ошибка распаковки архива {file_path}: {e}")
        raise e


@shared_task
def async_process_uploaded_files(base_upload_dir, uploaded_file_id):
    try:
        uploaded_file = UploadedFile.objects.get(id=uploaded_file_id)
        process_uploaded_files(base_upload_dir, uploaded_file)
        logger.info(f"Файлы из {base_upload_dir} успешно обработаны.")
    except Exception as e:
        logger.error(f"Ошибка обработки файлов из {base_upload_dir}: {e}")
        raise e
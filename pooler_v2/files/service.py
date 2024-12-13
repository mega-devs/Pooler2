import os
import zipfile
import re
import logging
from .models import ExtractedData
from pooler.views import remove_duplicate_lines
from pooler.utils import extract_country_from_filename

logger = logging.getLogger(__name__)


def handle_archive(file_path, save_path):
    try:
        with zipfile.ZipFile(file_path, 'r') as archive:
            extracted_folder = os.path.splitext(file_path)[0]  # Папка для распакованных файлов
            archive.extractall(extracted_folder)
        os.remove(file_path)  # Удаляем оригинальный архив после распаковки
    except zipfile.BadZipFile:
        raise ValueError("Invalid archive format")


def determine_origin(filename):
    if "smtp" in filename.lower():
        return "SMTP"
    elif "imap" in filename.lower():
        return "IMAP"
    elif "telegram" in filename.lower():
        return "TELEGRAM"
    else:
        return "MANUAL"


def process_uploaded_files(base_upload_dir, uploaded_file):
    """Проходит по всем распакованным директориям и извлекает данные."""
    try:
        for root, dirs, files in os.walk(base_upload_dir):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                process_file(file_path, file_name, uploaded_file)
    except Exception as e:
        logger.error(f"Ошибка обработки файлов из {base_upload_dir}: {e}")


def process_file(file_path, file_name, uploaded_file):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        num_duplicates = remove_duplicate_lines(file_path)
        logger.info(f"Удалено {num_duplicates} дублирующих строк из {file_name}")

        upload_origin = determine_origin(file_name)

        for line_number, line in enumerate(lines, start=1):
            match = re.match(r"([^@]+@[^:]+):(.+)", line.strip())
            if match:
                email, password = match.groups()
                provider = email.split('@')[1].split('.')[0].upper()
                country = extract_country_from_filename(file_name)

                ExtractedData.objects.create(
                    email=email,
                    password=password,
                    provider=provider,
                    country=country,
                    filename=file_name,
                    line_number=line_number,  # Сохранение номера строки
                    uploaded_file=uploaded_file,
                    upload_origin=upload_origin
                )

        logger.info(f"Данные из {file_name} успешно сохранены.")
    except Exception as e:
        logger.error(f"Ошибка обработки файла {file_name}: {e}")
import logging
import os

# создаем логгер
logger_temp_smtp = logging.getLogger('temp_smtp')
logger_temp_imap = logging.getLogger('temp_imap')
logger_smtp = logging.getLogger('smtp')
logger_imap = logging.getLogger('imap')

# настраиваем уровень логирования
logger_temp_smtp.setLevel(logging.DEBUG)
logger_temp_imap.setLevel(logging.DEBUG)
logger_smtp.setLevel(logging.DEBUG)
logger_imap.setLevel(logging.DEBUG)

# создаем форматтер
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# создаем обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# создаем обработчик для вывода в файл
file_handler_temp_smtp = logging.FileHandler(os.path.join("app", "data", "temp_logs", "temp_smtp.log"))
file_handler_temp_smtp.setLevel(logging.DEBUG)
file_handler_temp_smtp.setFormatter(formatter)

file_handler_temp_imap = logging.FileHandler(os.path.join("app", "data", "temp_logs", "temp_imap.log"))
file_handler_temp_imap.setLevel(logging.DEBUG)
file_handler_temp_imap.setFormatter(formatter)

file_handler_smtp = logging.FileHandler(os.path.join("app", "data", "full_logs", "smtp.log"))
file_handler_smtp.setLevel(logging.DEBUG)
file_handler_smtp.setFormatter(formatter)

file_handler_imap = logging.FileHandler(os.path.join("app", "data", "full_logs", "imap.log"))
file_handler_imap.setLevel(logging.DEBUG)
file_handler_imap.setFormatter(formatter)

# добавляем обработчики к логгерам
logger_temp_smtp.addHandler(console_handler)
logger_temp_smtp.addHandler(file_handler_temp_smtp)

logger_temp_imap.addHandler(console_handler)
logger_temp_imap.addHandler(file_handler_temp_imap)

logger_smtp.addHandler(console_handler)
logger_smtp.addHandler(file_handler_smtp)

logger_imap.addHandler(console_handler)
logger_imap.addHandler(file_handler_imap)

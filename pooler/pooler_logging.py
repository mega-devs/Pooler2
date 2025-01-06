import logging
import os

# create loggers
logger_temp_smtp = logging.getLogger('temp_smtp')
logger_temp_imap = logging.getLogger('temp_imap')
logger_smtp = logging.getLogger('smtp')
logger_imap = logging.getLogger('imap')

# configure logging level
logger_temp_smtp.setLevel(logging.DEBUG)
logger_temp_imap.setLevel(logging.DEBUG)
logger_smtp.setLevel(logging.DEBUG)
logger_imap.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# create handler for console output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# create log dirs
temp_logs_dir = os.path.join("app", "data", "temp_logs")
full_logs_dir = os.path.join("app", "data", "full_logs")

if not os.path.exists(temp_logs_dir):
    os.makedirs(temp_logs_dir)

if not os.path.exists(full_logs_dir):
    os.makedirs(full_logs_dir)

# create handler for file output
file_handler_temp_smtp = logging.FileHandler(os.path.join(temp_logs_dir, "temp_smtp.log"))
file_handler_temp_smtp.setLevel(logging.DEBUG)
file_handler_temp_smtp.setFormatter(formatter)

file_handler_temp_imap = logging.FileHandler(os.path.join(temp_logs_dir, "temp_imap.log"))
file_handler_temp_imap.setLevel(logging.DEBUG)
file_handler_temp_imap.setFormatter(formatter)

file_handler_smtp = logging.FileHandler(os.path.join(full_logs_dir, "smtp.log"))
file_handler_smtp.setLevel(logging.DEBUG)
file_handler_smtp.setFormatter(formatter)

file_handler_imap = logging.FileHandler(os.path.join(full_logs_dir, "imap.log"))
file_handler_imap.setLevel(logging.DEBUG)
file_handler_imap.setFormatter(formatter)

# add handlers to loggers
logger_temp_smtp.addHandler(console_handler)
logger_temp_smtp.addHandler(file_handler_temp_smtp)

logger_temp_imap.addHandler(console_handler)
logger_temp_imap.addHandler(file_handler_temp_imap)

logger_smtp.addHandler(console_handler)
logger_smtp.addHandler(file_handler_smtp)

logger_imap.addHandler(console_handler)
logger_imap.addHandler(file_handler_imap)

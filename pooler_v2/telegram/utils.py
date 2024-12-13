import re

def is_valid_telegram_username(username):
    return re.match(r'^(https://t\.me/|@)?[a-zA-Z0-9_]{5,32}$', username)
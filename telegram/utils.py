import json
import os
import re

import aiofiles
from django.http import JsonResponse


def is_valid_telegram_username(username):
    return re.match(r'^(https://t\.me/|@)?[a-zA-Z0-9_]{5,32}$', username)


async def parse_messages(client, channel):
    """
    Parses messages from a Telegram channel using the provided client.

    Retrieves the last 10 messages and extracts sender, date, and text.
    Returns a list of message dictionaries with formatted data.
    """
    messages = []
    async for message in (await client.iter_messages(channel, limit=10)):
        messages.append({
            'sender': message.sender_id,
            'date': message.date.strftime('%Y-%m-%d %H:%M:%S'),
            'text': message.text
        })
    return JsonResponse(messages, status=200, safe=False)


async def read_existing_messages(filename):
    """
    Reads and parses messages from a JSON file.

    Returns the parsed messages as a list if the file exists and has content.
    Returns an empty list if the file doesn't exist or is empty.
    """
    if os.path.exists(filename):
        async with aiofiles.open(filename, 'r', encoding='utf-8') as f:
            content = await f.read()
            return json.loads(content) if content else []
    return []


async def write_messages(filename, messages):
    """
    Writes messages to a JSON file asynchronously.

    Takes a filename and messages list as input parameters.
    Saves the messages with proper UTF-8 encoding and indentation.
    """
    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(messages, ensure_ascii=False, indent=4))

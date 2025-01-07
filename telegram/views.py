import json
import os
import re

import zipfile
from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from telethon import TelegramClient
from pooler.views import read_existing_messages, write_messages, parse_messages
from .utils import is_valid_telegram_username

from rest_framework.decorators import api_view
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


api_id = '29719825'
api_hash = '7fa19eeed8c2e5d35036fafb9a716f18'


@api_view(['POST'])
@csrf_exempt
async def telegram_add_channel(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        channel = data.get('channel')

        if not channel or not is_valid_telegram_username(channel):
            return JsonResponse({'status': 400, 'error': 'Invalid Telegram link or username'}, status=400)

        sanitized_channel = re.sub(r'\W+', '_', channel)

        async def main():
            async with TelegramClient('session_name', api_id, api_hash) as client:
                messages = await parse_messages(client, channel)
                return messages

        new_messages = await main()

        filename = os.path.join('app', 'data', f'parsed_messages_{sanitized_channel}.json')
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        existing_messages = await read_existing_messages(filename)

        existing_texts = {msg['text'] for msg in existing_messages}
        unique_messages = [msg for msg in new_messages if msg['text'] not in existing_texts]

        if unique_messages:
            combined_messages = existing_messages + unique_messages
            await write_messages(filename, combined_messages)
            return JsonResponse({'status': 200, 'messages': unique_messages, 'file': filename})
        else:
            return JsonResponse({'status': 200, 'message': 'No new unique messages to save.'})

    return JsonResponse({'status': 405, 'message': 'Invalid HTTP method'}, status=405)


@api_view(['GET'])
async def download_files_from_tg(links):
    async with TelegramClient('session_name', api_id, api_hash) as client:
        files = []
        for link in links:
            message = await client.get_messages(link, limit=1)
            if message and message[0].media:
                file_path = await message[0].download_media()
                files.append(file_path)
        return files


@api_view(['GET'])
@require_GET
async def get_combofiles_from_tg(request):
    links_file_path = os.path.join(settings.BASE_DIR, "data", "tg.txt")
    try:
        with open(links_file_path, 'r') as file:
            links = [link.strip() for link in file.readlines()]
    except FileNotFoundError:
        raise Http404("Telegram links file not found.")

    files = await download_files_from_tg(links)

    if not files:
        return JsonResponse({"error": "No files found"}, status=404)

    zip_filename = os.path.join(settings.BASE_DIR, "tg.zip")
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file in files:
            zipf.write(file, os.path.basename(file))

    try:
        response = FileResponse(open(zip_filename, 'rb'), as_attachment=True)
        response['Content-Disposition'] = 'attachment; filename="tg.zip"'
        return response
    finally:
        os.remove(zip_filename)
        for file in files:
            os.remove(file)


@api_view(['GET'])
async def download_files_from_tg(links):
    async with TelegramClient('session_name', api_id, api_hash) as client:
        files = []
        for link in links:
            message = await client.get_messages(link, limit=1)
            if message and message[0].media:
                file_path = await message[0].download_media()
                files.append(file_path)
        return files


@api_view(['GET'])
@require_GET
async def get_from_tg(request):
    links_file_path = os.path.join(settings.BASE_DIR, "data", "tg.txt")

    try:
        with open(links_file_path, 'r') as file:
            links = [link.strip() for link in file.readlines()]
    except FileNotFoundError:
        raise Http404("Telegram links file not found.")

    files = await download_files_from_tg(links)

    if not files:
        return JsonResponse({"error": "No files found"}, status=404)

    zip_filename = os.path.join(settings.BASE_DIR, "tg.zip")
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file in files:
            zipf.write(file, os.path.basename(file))

    try:
        response = FileResponse(open(zip_filename, 'rb'), as_attachment=True)
        response['Content-Disposition'] = 'attachment; filename="tg.zip"'
        return response
    finally:
        os.remove(zip_filename)
        for file in files:
            os.remove(file)
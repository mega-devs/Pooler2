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
from rest_framework.response import Response
from rest_framework import status


api_id = '29719825'
api_hash = '7fa19eeed8c2e5d35036fafb9a716f18'


@api_view(['POST'])
@csrf_exempt
async def telegram_add_channel(request):
    """Adds a Telegram channel and processes its messages.

    Takes a channel username/link in the request body and validates it.
    Returns processed messages and saves them to a JSON file."""
    if request.method == 'POST':
        data = json.loads(request.body)
        channel = data.get('channel')

        if not channel or not is_valid_telegram_username(channel):
            return Response(
                {'status': 'error', 'message': 'Invalid Telegram link or username'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

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
            return Response({
                'status': 'success',
                'messages': unique_messages,
                'file': filename
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'success',
                'message': 'No new unique messages to save.'
            }, status=status.HTTP_200_OK)

    return Response({
        'status': 'error', 
        'message': 'Invalid HTTP method'
    }, status=status.HTTP_405_METHOD_NOT_ALLOWED)


from asgiref.sync import async_to_sync

@api_view(['POST'])
def download_files_from_tg(request):
    """
    Downloads files from Telegram links.

    Takes a list of Telegram message links as input.
    Returns a JSON response with downloaded file paths.
    """
    links = request.data.get('links', [])
    
    if not isinstance(links, list):
        return JsonResponse({'error': 'Invalid input. "links" must be a list.'}, status=400)

    def sync_download():
        async def download():
            async with TelegramClient('session_name', api_id, api_hash) as client:
                files = []
                for link in links:
                    try:
                        message = await client.get_messages(link, limit=1)
                        if message and message[0].media:
                            file_path = await message[0].download_media()
                            files.append(file_path)
                    except Exception as e:
                        return {'error': f"Failed to process link {link}. Error: {str(e)}"}
                return {'files': files}

        return async_to_sync(download)()

    result = sync_download()
    
    if 'error' in result:
        return JsonResponse(result, status=500)
    
    return JsonResponse(result)
    

@api_view(['GET'])
@require_GET
async def get_combofiles_from_tg(request):
    """Downloads files from Telegram links stored in a text file.

    Creates a zip archive containing all downloaded files.
    Returns the zip file as a downloadable response."""
    links_file_path = os.path.join(settings.BASE_DIR, "data", "tg.txt")
    try:
        links_file_path = os.path.join(settings.BASE_DIR, "data", "tg.txt")
        with open(links_file_path, 'r') as file:
            links = [link.strip() for link in file.readlines()]
    except FileNotFoundError:
        return Response({
            'status': 'error',
            'message': 'Telegram links file not found'
        }, status=status.HTTP_404_NOT_FOUND)

    files = await download_files_from_tg(links)

    if not files:
        return Response({
            'status': 'error',
            'message': 'No files found'
        }, status=status.HTTP_404_NOT_FOUND)

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
@require_GET
async def get_from_tg(request):
    """Downloads files from Telegram links stored in a text file.

    Creates a zip archive containing all downloaded files.
    Returns the zip file as a downloadable response."""
    links_file_path = os.path.join(settings.BASE_DIR, "data", "tg.txt")

    try:
        links_file_path = os.path.join(settings.BASE_DIR, "data", "tg.txt")
        with open(links_file_path, 'r') as file:
            links = [link.strip() for link in file.readlines()]
    except FileNotFoundError:
        return Response({
            'status': 'error',
            'message': 'Telegram links file not found'
        }, status=status.HTTP_404_NOT_FOUND)

    files = await download_files_from_tg(links)

    if not files:
        return Response({
            'status': 'error',
            'message': 'No files found'
        }, status=status.HTTP_404_NOT_FOUND)

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
            
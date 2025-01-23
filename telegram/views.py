import json
import os
import re
import zipfile
from datetime import datetime

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from telethon import TelegramClient
from asgiref.sync import async_to_sync

from django.conf import settings
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

import rest_framework.decorators as decorator
from rest_framework.response import Response
from rest_framework import status

from adrf.decorators import api_view

from .utils import is_valid_telegram_username, parse_messages, read_existing_messages, write_messages


api_id = '29719825'
api_hash = '7fa19eeed8c2e5d35036fafb9a716f18'

ALLOWED_EXTENSIONS = [
    '.txt', '.md', '.rtf', '.csv', '.log',
    '.py', '.js', '.html', '.css', '.java',
    '.c', '.cpp', '.json', '.xml', '.yaml',
    '.ini', '.sh', '.bat',
    '.zip', '.rar', '.7z', '.tar', '.gz',
    '.bz2', '.xz',
    '.docx', '.xlsx', '.pptx'
]


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'channel': openapi.Schema(type=openapi.TYPE_STRING, description="The Telegram channel's username or link."),
        },
        required=['channel']
    ),
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'messages': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'file': openapi.Schema(type=openapi.TYPE_STRING, description="Path to the saved JSON file.")
                }
            )
        ),
        400: openapi.Response(
            'Bad Request',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'message': openapi.Schema(type=openapi.TYPE_STRING)}
            )
        ),
        405: openapi.Response(
            'Method Not Allowed',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'message': openapi.Schema(type=openapi.TYPE_STRING)}
            )
        ),
    }
)
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
        unique_messages = [msg for msg in new_messages if isinstance(msg, dict) and 'text' in msg and msg['text'] not in existing_texts]

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


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'links': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(type=openapi.TYPE_STRING),
                description="List of Telegram message links."
            ),
            'date': openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                description="Filter files by date in YYYY-MM-DD format (optional)."
            ),
            'max_size': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="Maximum file size in MB (optional)."
            ),
        },
        required=['links']
    ),
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'files': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                }
            )
        ),
        400: openapi.Response(
            'Bad Request',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={'error': openapi.Schema(type=openapi.TYPE_STRING)}
            )
        ),
        500: openapi.Response(
            'Server Error',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={'error': openapi.Schema(type=openapi.TYPE_STRING)}
            )
        ),
    }
)
@api_view(['POST'])
def download_files_from_tg(request):
    links = request.data.get('links', [])
    date_str = request.data.get('date', None)
    max_size = request.data.get('max_size', None)

    if not isinstance(links, list):
        return JsonResponse({'error': 'Invalid input. "links" must be a list.'}, status=400)

    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
    else:
        filter_date = None

    if max_size is not None:
        try:
            MAX_SIZE_BYTES = int(max_size) * 1024 * 1024
        except ValueError:
            return JsonResponse({'error': 'Invalid max_size. Must be an integer.'}, status=400)
    else:
        MAX_SIZE_BYTES = 300 * 1024 * 1024

    def sync_download():
        async def download():
            async with TelegramClient('session_name', api_id, api_hash) as client:
                files = []
                for link in links:
                    try:
                        message = await client.get_messages(link, limit=1)
                        if message and message[0].media:
                            media = message[0].media
                            message_date = message[0].date.date()

                            if filter_date and message_date != filter_date:
                                continue

                            if media:
                                _, extension = os.path.splitext(media.file_name or '')
                                if extension.lower() not in ALLOWED_EXTENSIONS:
                                    continue
                                file_path = await message[0].download_media()
                                file_size = os.path.getsize(file_path)
                                if file_size > MAX_SIZE_BYTES:
                                    os.remove(file_path)
                                    continue
                                files.append(file_path)
                    except Exception as e:
                        return {'error': f"Failed to process link {link}. Error: {str(e)}"}
                return {'files': files}

        return async_to_sync(download)()

    result = sync_download()

    if 'error' in result:
        return JsonResponse(result, status=500)

    return JsonResponse(result)


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter(
            'date',
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Filter files by date in YYYY-MM-DD format (optional)."
        ),
        openapi.Parameter(
            'max_size',
            openapi.IN_QUERY,
            type=openapi.TYPE_INTEGER,
            description="Maximum file size in MB (optional)."
        ),
    ],
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        400: openapi.Response(
            'Bad Request',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'message': openapi.Schema(type=openapi.TYPE_STRING)}
            )
        ),
        404: openapi.Response(
            'Not Found',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'message': openapi.Schema(type=openapi.TYPE_STRING)}
            )
        ),
    }
)
@api_view(['GET'])
@require_GET
async def get_combofiles_from_tg(request):
    date_str = request.GET.get('date', None)
    max_size = request.GET.get('max_size', None)

    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD.'
            }, status=status.HTTP_400_BAD_REQUEST)
    else:
        filter_date = None

    links_file_path = os.path.join(settings.BASE_DIR, "data", "tg.txt")
    try:
        with open(links_file_path, 'r') as file:
            links = [link.strip() for link in file.readlines()]
    except FileNotFoundError:
        return Response({
            'status': 'error',
            'message': 'Telegram links file not found'
        }, status=status.HTTP_404_NOT_FOUND)

    files = await download_files_from_tg({
        "links": links,
        "date": filter_date,
        "max_size": max_size
    })

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


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter(
            'date',
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Filter files by date in YYYY-MM-DD format (optional)."
        ),
        openapi.Parameter(
            'max_size',
            openapi.IN_QUERY,
            type=openapi.TYPE_INTEGER,
            description="Maximum file size in MB (optional)."
        ),
    ],
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        400: openapi.Response(
            'Bad Request',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'message': openapi.Schema(type=openapi.TYPE_STRING)}
            )
        ),
        404: openapi.Response(
            'Not Found',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'message': openapi.Schema(type=openapi.TYPE_STRING)}
            )
        ),
    }
)
@api_view(['GET'])
@require_GET
async def get_from_tg(request):
    links_file_path = os.path.join(settings.BASE_DIR, "data", "tg.txt")
    date_str = request.GET.get('date', None)
    max_size = request.GET.get('max_size', None)

    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD.'
            }, status=status.HTTP_400_BAD_REQUEST)
    else:
        filter_date = None

    try:
        with open(links_file_path, 'r') as file:
            links = [link.strip() for link in file.readlines()]
    except FileNotFoundError:
        return Response({
            'status': 'error',
            'message': 'Telegram links file not found'
        }, status=status.HTTP_404_NOT_FOUND)

    files = await download_files_from_tg({
        "links": links,
        "date": filter_date,
        "max_size": max_size
    })

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

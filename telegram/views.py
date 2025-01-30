import json
import os
import re
import zipfile
from datetime import datetime

import requests
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
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

from .serializers import URLFileUploadSerializer, LocalFileUploadSerializer
from .utils import is_valid_telegram_username, parse_messages, read_existing_messages, write_messages, save_file

api_id = '29719825'
api_hash = '7fa19eeed8c2e5d35036fafb9a716f18'

from root.logger import getLogger

logger = getLogger(__name__)

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
    logger.info("Received request to add Telegram channel.")
    
    if request.method == 'POST':
        data = json.loads(request.body)
        channel = data.get('channel')
        logger.info(f"Processing channel: {channel}")

        if not channel or not is_valid_telegram_username(channel):
            logger.error("Invalid Telegram link or username.")
            return Response(
                {'status': 'error', 'message': 'Invalid Telegram link or username'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        sanitized_channel = re.sub(r'\W+', '_', channel)

        async def main():
            async with TelegramClient('session_name', api_id, api_hash) as client:
                messages = await parse_messages(client, channel)
                return messages.data['messages']

        new_messages = await main()
        logger.info(f"Retrieved {len(new_messages)} messages from channel.")

        filename = os.path.join('app', 'data', f'parsed_messages_{sanitized_channel}.json')
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        existing_messages = await read_existing_messages(filename)
        logger.info(f"Read {len(existing_messages)} existing messages from file.")

        existing_texts = {msg['text'] for msg in existing_messages}
        unique_messages = [msg for msg in new_messages if isinstance(msg, dict) and 'text' in msg and msg['text'] not in existing_texts]

        if unique_messages:
            combined_messages = existing_messages + unique_messages
            await write_messages(filename, combined_messages)
            logger.info(f"Saved {len(unique_messages)} new unique messages to file.")
            return Response({
                'status': 'success',
                'messages': unique_messages,
                'file': filename
            }, status=status.HTTP_200_OK)
        else:
            logger.info("No new unique messages to save.")
            return Response({
                'status': 'success',
                'message': 'No new unique messages to save.'
            }, status=status.HTTP_200_OK)

    logger.error("Invalid HTTP method.")
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
    logger.info("Received request to download files from Telegram.")
    links = request.data.get('links', [])
    date_str = request.data.get('date', None)
    max_size = request.data.get('max_size', None)

    if not isinstance(links, list):
        logger.error('Invalid input. "links" must be a list.')
        return JsonResponse({'error': 'Invalid input. "links" must be a list.'}, status=400)

    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            logger.error('Invalid date format. Use YYYY-MM-DD.')
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
    else:
        filter_date = None

    if max_size is not None:
        try:
            MAX_SIZE_BYTES = int(max_size) * 1024 * 1024
        except ValueError:
            logger.error('Invalid max_size. Must be an integer.')
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
                        logger.error(f"Failed to process link {link}. Error: {str(e)}")
                        return {'error': f"Failed to process link {link}. Error: {str(e)}"}
                logger.info(f"Successfully downloaded files: {files}")
                return {'files': files}

        return async_to_sync(download)()

    result = sync_download()

    if 'error' in result:
        logger.error(f"Error in downloading files: {result['error']}")
        return JsonResponse(result, status=500)

    logger.info("Files downloaded successfully.")
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
    logger.info("Received request to get_combofiles_from_tg")
    date_str = request.GET.get('date', None)
    max_size = request.GET.get('max_size', None)

    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            logger.error("Invalid date format: %s", date_str)
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
        logger.error("Telegram links file not found at path: %s", links_file_path)
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
        logger.info("No files found for the given criteria")
        return Response({
            'status': 'error',
            'message': 'No files found'
        }, status=status.HTTP_404_NOT_FOUND)

    zip_filename = os.path.join(settings.BASE_DIR, "tg.zip")
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file in files:
            zipf.write(file, os.path.basename(file))

    try:
        logger.info("Sending zip file: %s", zip_filename)
        response = FileResponse(open(zip_filename, 'rb'), as_attachment=True)
        response['Content-Disposition'] = 'attachment; filename="tg.zip"'
        return response
    finally:
        os.remove(zip_filename)
        for file in files:
            os.remove(file)
        logger.info("Cleaned up temporary files")


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
    logger.info("Received request to get files from Telegram.")
    links_file_path = os.path.join(settings.BASE_DIR, "data", "tg.txt")
    date_str = request.GET.get('date', None)
    max_size = request.GET.get('max_size', None)

    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            logger.error("Invalid date format provided.")
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
        logger.error("Telegram links file not found.")
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
        logger.warning("No files found for the given criteria.")
        return Response({
            'status': 'error',
            'message': 'No files found'
        }, status=status.HTTP_404_NOT_FOUND)

    zip_filename = os.path.join(settings.BASE_DIR, "tg.zip")
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file in files:
            zipf.write(file, os.path.basename(file))

    try:
        logger.info("Files zipped successfully, preparing response.")
        response = FileResponse(open(zip_filename, 'rb'), as_attachment=True)
        response['Content-Disposition'] = 'attachment; filename="tg.zip"'
        return response
    finally:
        logger.info("Cleaning up temporary files.")
        os.remove(zip_filename)
        for file in files:
            os.remove(file)


class LocalFileUploadView(APIView):
    def post(self, request):
        logger.info("LocalFileUploadView POST request received.")
        serializer = LocalFileUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['file']
            file_path = os.path.join(settings.COMBO_FILES_DIR, file.name)
            logger.info(f"Received file: {file.name}, saving to {file_path}")

            try:
                save_file(file, file_path)
                logger.info(f"File {file.name} uploaded successfully.")
                return Response({'message': 'File uploaded successfully from local'}, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Failed to save the file: {e}")
                return Response({'error': f'Failed to save the file: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.warning(f"Serializer errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class URLFileUploadView(APIView):
    def post(self, request):
        logger.info("URLFileUploadView POST request received.")
        serializer = URLFileUploadSerializer(data=request.data)
        if serializer.is_valid():
            file_url = serializer.validated_data['file_url']
            logger.info(f"Received file URL: {file_url}")

            try:
                response = requests.get(file_url)
                response.raise_for_status()
                file_name = file_url.split("/")[-1]
                file_path = os.path.join(settings.COMBO_FILES_DIR, file_name)

                save_file(response.content, file_path)
                logger.info(f"File {file_name} uploaded successfully from URL.")
                return Response({'message': 'File uploaded successfully from URL'}, status=status.HTTP_201_CREATED)

            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to retrieve file from the URL: {e}")
                return Response({'error': 'Failed to retrieve file from the URL'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Failed to save the file: {e}")
                return Response({f"error': 'Failed to save the file: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.warning(f"Serializer errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

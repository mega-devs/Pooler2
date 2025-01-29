import asyncio
import base64
import logging
import os
from pathlib import Path
import zipfile
import aiofiles
import requests

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from celery.result import AsyncResult

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action

import adrf.decorators as adrf

from .apps import PoolerConfig

from .utils import extract_country_from_filename, read_logs, clear_logs
from .tasks import check_imap_emails_from_db, check_smtp_emails_from_db, run_selected_tests
from files.models import ExtractedData

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
from root.logger import getLogger

logger = getLogger(__name__)


class RunTestViewSet(ViewSet):
    queryset = None
    @action(detail=False, methods=['get'], url_path='', url_name='list')
    def lists(self, request):
        logger.info("Retrieving test files list")
        test_files = {}
        base_dir = Path(settings.BASE_DIR.parent)
        files = [file for file in base_dir.rglob("tests.py") if file.is_file()]
        for file in files:
            app_name = file.parent.name
            test_files[app_name] = str(file.relative_to(base_dir))
        logger.debug(f"Found {len(test_files)} test files")
        return Response({"result": test_files})

    @action(detail=False, methods=['post'], url_path='run', url_name='run')
    def run(self, request):
        logger.info("Running selected tests")
        test_list = request.data.get("tests", [])
        if not isinstance(test_list, list):
            logger.error("Invalid test_list format - must be a list")
            return Response({"error": "test_list must be a list"}, status=400)

        base_dir = Path(settings.BASE_DIR.parent)
        invalid_tests = [
            test for test in test_list if not (base_dir / test).exists()
        ]
        
        if invalid_tests:
            logger.error(f"Invalid test files found: {invalid_tests}")
            return Response(
                {"error": "The following test files do not exist", "invalid": invalid_tests},
                status=400,
            )

        logger.info(f"Starting test execution for {len(test_list)} tests")
        task = run_selected_tests.delay(test_list)
        return Response({"task_id": task.id}, status=202)

    @action(detail=True, methods=['get'], url_path='results', url_name='results')
    def results(self, request, pk=None):
        logger.info(f"Checking results for task {pk}")
        task = AsyncResult(pk)
        if task.state == "PENDING":
            logger.debug(f"Task {pk} is still pending")
            return Response({"status": "PENDING", "result": task.result})
        elif task.state == "SUCCESS":
            logger.info(f"Task {pk} completed successfully")
            return Response({"status": "SUCCESS", "result": task.result})
        elif task.state == "FAILURE":
            logger.error(f"Task {pk} failed: {task.result}")
            return Response({"status": "FAILURE", "error": str(task.result)})
        else:
            logger.debug(f"Task {pk} status: {task.state}")
            return Response({"status": task.state})

@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            'Redirect URL',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'redirect': openapi.Schema(type=openapi.TYPE_STRING)}
            )
        )
    }
)
@api_view(['GET'])
@require_http_methods(["GET"])
def redirect_to_panel(request):
    """
    Redirects user to the main panel view.

    This view function handles GET requests and redirects to the panel URL 
    using Django's reverse_lazy function to avoid any circular import issues.
    """
    return JsonResponse({'redirect': reverse_lazy('pooler:panel')})


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'active_page': openapi.Schema(type=openapi.TYPE_STRING),
                    'count_of_smtp_valid': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'count_of_smtp_invalid': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'count_of_smtp': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'count_of_imap': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'count_imap_valid': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'count_imap_invalid': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'smtp_checked': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'imap_checked': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )
        )
    }
)
@cache_page(60 * 2)
@api_view(['GET'])
@require_http_methods(["GET"])
def panel(request):
    """
    Main panel view that displays dashboard statistics for SMTP and IMAP data.
    
    Retrieves counts of valid/invalid SMTP and IMAP records from ExtractedData model.
    Returns JSON response with statistics context data.
    """
    smtp_valid_count = ExtractedData.objects.filter(smtp_is_valid=True).count()
    imap_valid_count = ExtractedData.objects.filter(imap_is_valid=True).count()
    smtp_invalid_count = ExtractedData.objects.filter(smtp_is_valid=False).count()
    imap_invalid_count = ExtractedData.objects.filter(imap_is_valid=False).count()
    smtp_checked = smtp_invalid_count + smtp_valid_count
    imap_checked = imap_invalid_count + imap_valid_count
    smtp_all_count = ExtractedData.objects.all().count()
    imap_all_count = ExtractedData.objects.all().count()
    
    data = {
        'active_page': "dashboard",
        'count_of_smtp_valid': smtp_valid_count,
        'count_of_smtp_invalid': smtp_invalid_count,
        'count_of_smtp': smtp_all_count,
        'count_of_imap': imap_all_count,
        'count_imap_valid': imap_valid_count,
        'count_imap_invalid': imap_invalid_count,
        'smtp_checked': smtp_checked,
        'imap_checked': imap_checked
    }
    return JsonResponse(data)


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'active_page': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        )
    }
)
@swagger_auto_schema(
    method='post',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'active_page': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        )
    }
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@require_http_methods(["GET", "POST"])
def panel_settings(request):
    """
    Returns JSON response for settings data.
    
    This view function handles both GET and POST requests and requires user authentication.    
    Returns JSON response with active page context set to 'settings'.
    """
    data = {'active_page': "settings"}
    return JsonResponse(data)


@api_view(['POST'])
@csrf_exempt
def upload_file_by_url(request):
    """
    Handles file upload via URL endpoint.    

    Downloads file from provided URL and saves it to appropriate directory based on country.
    Returns JSON response with status and filename or error details.
    """
    if request.method == 'POST':
        try:
            file_url = request.data.get('url')
            logger.info(f"Attempting to upload file from URL: {file_url}")

            if not file_url:
                logger.error("No URL provided for file upload")
                return Response({'status': 404, 'error': 'No URL provided'}, status=status.HTTP_400_BAD_REQUEST)

            response = requests.get(file_url)
            if response.status_code == 200:
                filename = os.path.basename(file_url).replace(" ", "_")
                country = extract_country_from_filename(filename)
                logger.info(f"File download successful. Filename: {filename}, Country: {country}")

                if country:
                    save_path = os.path.join('app', 'data', 'combofiles', country)
                else:
                    save_path = os.path.join('app', 'data', 'combofiles')

                os.makedirs(save_path, exist_ok=True)
                filepath = os.path.join(save_path, filename)
                
                with open(filepath, 'wb') as file:
                    file.write(response.content)
                logger.info(f"File saved successfully at: {filepath}")

                return Response({'status': 200, 'filename': filename}, status=status.HTTP_200_OK)
            else:
                logger.error(f"Failed to download file. Status code: {response.status_code}")
                return Response({'status': 404, 'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"Error during file upload: {str(e)}")
            return Response({'status': 500, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        logger.warning("Invalid HTTP method for file upload")
        return Response({'status': 405, 'error': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    

@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        500: openapi.Response(
            'Error',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    }
)
@api_view(['GET'])
@require_GET
def check_smtp_view(request):
    """
    Async view to check SMTP emails from database.

    Creates an event loop and runs the check_smtp_emails_from_db task.
    Returns JSON response with status on success or error response on failure.
    """
    logger.info("Starting SMTP check")
    try:
        asyncio.run(check_smtp_emails_from_db())
        logger.info("SMTP check completed successfully")
        return JsonResponse({'status': 'success'}, status=200)
    except Exception as e:
        logger.exception(f"Error during SMTP check: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        500: openapi.Response(
            'Error',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    }
)
@api_view(['GET'])
@require_GET
def check_imap_view(request):
    """
    Async view to check IMAP emails from database.
    
    Creates an event loop and runs the check_imap_emails_from_db task.
    Returns JSON response with status on success or error response on failure.
    """
    try:
        asyncio.run(check_imap_emails_from_db())
        return JsonResponse({'status': 'success'}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'smtp_logs': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'color': openapi.Schema(type=openapi.TYPE_STRING),
                                'thread_num': openapi.Schema(type=openapi.TYPE_STRING),
                                'timestamp': openapi.Schema(type=openapi.TYPE_STRING),
                                'server': openapi.Schema(type=openapi.TYPE_STRING),
                                'user': openapi.Schema(type=openapi.TYPE_STRING),
                                'port': openapi.Schema(type=openapi.TYPE_STRING),
                                'response': openapi.Schema(type=openapi.TYPE_STRING),
                                'status': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        )
                    ),
                    'imap_logs': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'color': openapi.Schema(type=openapi.TYPE_STRING),
                                'thread_num': openapi.Schema(type=openapi.TYPE_STRING),
                                'timestamp': openapi.Schema(type=openapi.TYPE_STRING),
                                'server': openapi.Schema(type=openapi.TYPE_STRING),
                                'user': openapi.Schema(type=openapi.TYPE_STRING),
                                'port': openapi.Schema(type=openapi.TYPE_STRING),
                                'status': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        )
                    ),
                    'socks_logs': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'thread_num': openapi.Schema(type=openapi.TYPE_STRING),
                                'timestamp': openapi.Schema(type=openapi.TYPE_STRING),
                                'proxy_port': openapi.Schema(type=openapi.TYPE_STRING),
                                'result': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        )
                    ),
                    'url_fetch_logs': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'timestamp': openapi.Schema(type=openapi.TYPE_STRING),
                                'filename': openapi.Schema(type=openapi.TYPE_STRING),
                                'url': openapi.Schema(type=openapi.TYPE_STRING),
                                'size': openapi.Schema(type=openapi.TYPE_STRING),
                                'lines': openapi.Schema(type=openapi.TYPE_STRING),
                                'status': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        )
                    ),
                    'telegram_logs': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'timestamp': openapi.Schema(type=openapi.TYPE_STRING),
                                'filename': openapi.Schema(type=openapi.TYPE_STRING),
                                'url': openapi.Schema(type=openapi.TYPE_STRING),
                                'size': openapi.Schema(type=openapi.TYPE_STRING),
                                'lines': openapi.Schema(type=openapi.TYPE_STRING),
                                'status': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        )
                    )
                }
            )
        ),
        500: openapi.Response(
            'Error',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    }
)
@cache_page(60 * 2)
@adrf.api_view(['GET'])
async def get_logs(request):
    """
    Retrieves all types of logs with parsed columns for frontend display.
    Returns structured JSON with separate arrays for each log type.
    """
    async def parse_smtp_log(line):
        try:
            parts = line.strip().split('|')
            if len(parts) >= 6:
                return {
                    'thread_num': parts[0],
                    'timestamp': parts[1],
                    'server': parts[2],
                    'user': parts[3],
                    'port': parts[4],
                    'response': parts[5],
                    'status': parts[6]
                }
            return None
        except:
            return None

    async def parse_imap_log(line):
        try:
            parts = line.strip().split('|')
            if len(parts) >= 6:
                return {
                    'thread_num': parts[0],
                    'timestamp': parts[1],
                    'server': parts[2],
                    'user': parts[3],
                    'port': parts[4],
                    'status': parts[5]
                }
            return None
        except:
            return None

    async def parse_socks_log(line):
        try:
            parts = line.strip().split('|')
            if len(parts) >= 4:
                return {
                    'thread_num': parts[0],
                    'timestamp': parts[1],
                    'proxy_port': parts[2],
                    'result': parts[3]
                }
            return None
        except:
            return None

    async def parse_url_fetch_log(line):
        try:
            parts = line.strip().split('|')
            if len(parts) >= 6:
                return {
                    'timestamp': parts[0],
                    'filename': parts[1],
                    'url': parts[2],
                    'size': parts[3],
                    'lines': parts[4],
                    'status': parts[5]
                }
            return None
        except:
            return None

    async def parse_telegram_log(line):
        try:
            parts = line.strip().split('|')
            if len(parts) >= 6:
                return {
                    'timestamp': parts[0],
                    'filename': parts[1],
                    'url': parts[2],
                    'size': parts[3],
                    'lines': parts[4],
                    'status': parts[5]
                }
            return None
        except:
            return None

    try:
        # Read and parse each log file
        smtp_logs = []
        imap_logs = []
        socks_logs = []
        url_fetch_logs = []
        telegram_logs = []
        logs = await read_logs(0)

        async with aiofiles.open(settings.LOG_FILES['smtp'], 'r') as f:
            lines = await f.readlines()
            smtp_logs = [log for line in lines if (log := await parse_smtp_log(line)) is not None]

        async with aiofiles.open(settings.LOG_FILES['imap'], 'r') as f:
            lines = await f.readlines()
            imap_logs = [log for line in lines if (log := await parse_imap_log(line)) is not None]

        async with aiofiles.open(settings.LOG_FILES['socks'], 'r') as f:
            lines = await f.readlines()
            socks_logs = [log for line in lines if (log := await parse_socks_log(line)) is not None]

        async with aiofiles.open(settings.LOG_FILES['url_fetch'], 'r') as f:
            lines = await f.readlines()
            url_fetch_logs = [log for line in lines if (log := await parse_url_fetch_log(line)) is not None]

        async with aiofiles.open(settings.LOG_FILES['telegram_fetch'], 'r') as f:
            lines = await f.readlines()
            telegram_logs = [log for line in lines if (log := await parse_telegram_log(line)) is not None]

        return JsonResponse({
            'logs': logs,
            'smtp_logs': smtp_logs,
            'imap_logs': imap_logs,
            'socks_logs': socks_logs,
            'url_fetch_logs': url_fetch_logs,
            'telegram_logs': telegram_logs            
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@swagger_auto_schema(
    method='post',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        500: openapi.Response(
            'Error',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    }
)
@adrf.api_view(['POST'])
async def clear_temp_logs(request):
    """
    Clears the temporary SMTP and IMAP log files.
    
    Creates empty log files if they don't exist.
    Returns a JSON response indicating success or failure."""
    logger.info("Attempting to clear temporary logs")
    smtp_log_path = os.path.join("app", "data", "temp_logs", 'temp_smtp.log')
    imap_log_path = os.path.join("app", "data", "temp_logs", 'temp_imap.log')

    try:
        if os.path.exists(smtp_log_path):
            async with aiofiles.open(smtp_log_path, 'w') as smtp_file:
                await smtp_file.write('')
                logger.debug("SMTP temp log cleared")
        if os.path.exists(imap_log_path):
            async with aiofiles.open(imap_log_path, 'w') as imap_file:
                await imap_file.write('')
                logger.debug("IMAP temp log cleared")
        logger.info("All temporary logs cleared successfully")
        return JsonResponse({"message": "Logs cleared successfully"}, status=200)
    except Exception as e:
        logger.exception(f"Error clearing temporary logs: {str(e)}")
        return JsonResponse({"message": str(e)}, status=500)  
     

@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        404: openapi.Response(
            'Log files not found',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        500: openapi.Response(
            'Error',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    }
)
@api_view(['GET'])
def clear_full_logs(request):
    """
    Clears the full SMTP and IMAP log files.

    Removes the log files from the filesystem if they exist.
    Returns a JSON response indicating success or failure.
    """

    smtp_log_path = os.path.join(settings.BASE_DIR, "app", "data", "temp_logs", 'smtp.log')
    imap_log_path = os.path.join(settings.BASE_DIR, "app", "data", "temp_logs", 'imap.log')
    socks_log_path = os.path.join(settings.BASE_DIR, "app", "data", "temp_logs", 'socks.log')
    telegram_log_path = os.path.join(settings.BASE_DIR, "app", "data", "temp_logs", 'telegram.log')
    url_log_path = os.path.join(settings.BASE_DIR, "app", "data", "temp_logs", 'url.log')

    clear_smtp = request.data.get('smtp', False)
    clear_imap = request.data.get('imap', False)
    clear_socks = request.data.get('socks', False)
    clear_telegram = request.data.get('telegram', False)
    clear_url = request.data.get('url', False)

    try:
        if clear_smtp:
            return clear_logs(smtp_log_path)
        if clear_imap:
            return clear_logs(imap_log_path)
        if clear_socks:
            return clear_logs(socks_log_path)
        if clear_telegram:
            return clear_logs(telegram_log_path)
        if clear_url:
            return clear_logs(url_log_path)

        return Response({"message": "No logs specified for clearing"}, status=400)

    except Exception as e:
        return Response({"message": str(e)}, status=500)
    

@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'smtp': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                    'imap': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                }
            )
        ),
        404: openapi.Response(
            'Not Found',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
    }
)
@cache_page(60 * 2)
@api_view(['GET'])
def download_logs_file(request):
    """
    Downloads SMTP and IMAP log files as JSON.

    Reads the logs from the data/full_logs directory and returns them in JSON format.
    Returns a JSON response containing the contents of both log files."""

    directory = os.path.join(settings.BASE_DIR, 'data', 'full_logs')
    log_files = {"smtp": "smtp.log", "imap": "imap.log"}
    logs_data = {}

    for log_type, filename in log_files.items():
        file_path = os.path.join(directory, filename)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                logs_data[log_type] = f.read().splitlines()
        else:
            logs_data[log_type] = []

    return Response(logs_data, status=200)


@api_view(['GET'])
@require_GET
def get_valid_smtp(request):
    """
    Returns all valid SMTP entries from ExtractedData.
    """
    valid_smtp = ExtractedData.objects.filter(smtp_is_valid=True).values(
        'email', 'password', 'provider', 'country', 'filename'
    )
    return JsonResponse({'valid_smtp': list(valid_smtp)})


@api_view(['GET']) 
@require_GET
def get_valid_imap(request):
    """
    Returns all valid IMAP entries from ExtractedData.
    """
    valid_imap = ExtractedData.objects.filter(imap_is_valid=True).values(
        'email', 'password', 'provider', 'country', 'filename'
    )
    return JsonResponse({'valid_imap': list(valid_imap)})


@api_view(['GET', 'POST'])
def dynamic_settings(request):
    if request.method == 'POST':
        # Set a dynamic setting
        key = request.data.get('key')
        value = request.data.get('value')

        if not key or value is None:
            return JsonResponse({'error': 'Key and value are required'}, status=400)

        if key == 'debug':
            is_enabled = request.data.get('debug', True)
            setattr(settings, "LOGGING_ENABLED", is_enabled)

            # to persist across multiple workers
            cache.set('LOGGING_ENABLED', is_enabled, timeout=None)
            logger = logging.getLogger()
            if is_enabled:
                logger.setLevel(logging.INFO)
            else:
                logger.setLevel(logging.CRITICAL + 1)

        PoolerConfig.set_setting(key, value)
        return JsonResponse({'message': f'Setting {key} updated successfully'})

    elif request.method == 'GET':
        # Retrieve all dynamic settings
        return JsonResponse(PoolerConfig.settings)

#     imap_driver = ImapDriver()
#     imap_results = []
#
#     file_path = os.path.join(settings.BASE_DIR, 'app', 'data', 'combofiles', filename)
#
#     if filename.endswith('.zip'):
#         with zipfile.ZipFile(file_path, 'r') as zip_file:
#             for zip_info in zip_file.infolist():
#                 if not zip_info.is_dir():
#                     with io.TextIOWrapper(zip_file.open(zip_info), encoding='utf-8') as f:
#                         lines = f.readlines()
#                         chunks_size = 100
#                         chunked_lines = list(chunks(lines, chunks_size))
#                         tasks = [process_chunk(chunk, imap_driver, imap_results) for chunk in chunked_lines]
#                         await asyncio.gather(*tasks)
#     else:
#         async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
#             lines = await f.readlines()
#             chunks_size = 100
#             chunked_lines = list(chunks(lines, chunks_size))
#             tasks = [process_chunk(chunk, imap_driver, imap_results) for chunk in chunked_lines]
#             await asyncio.gather(*tasks)
#
#     return imap_results

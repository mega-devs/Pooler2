import asyncio
import io
import json
import logging
import os
import zipfile

# third-party imports
import aiofiles
import chardet
import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import (FileResponse, Http404, HttpResponse, HttpResponseRedirect,
        JsonResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import (require_GET, require_http_methods,
                         require_POST)
from rest_framework.decorators import api_view

# local imports
from .pooler_logging import logger_temp_smtp
from .utils import (check_imap_emails_from_db, check_smtp_emails_from_db,
    check_smtp_imap_emails_from_zip, chunks,
    extract_country_from_filename, get_email_bd_data)
from files.models import ExtractedData
import mimetypes


os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
logger = logging.getLogger(__name__)


@api_view(['GET'])
@require_http_methods(["GET"])
def redirect_to_panel(request):
    """
    Redirects user to the main panel view.
    
    This view function handles GET requests and redirects to the panel URL 
    using Django's reverse_lazy function to avoid any circular import issues.
    """
    return JsonResponse({'redirect': reverse_lazy('pooler:panel')})


@api_view(['GET'])
# @login_required(login_url='/users/login/')
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
    
    data = {
        'active_page': "dashboard",
        'count_of_smtp_valid': smtp_valid_count,
        'count_of_smtp_invalid': smtp_invalid_count,
        'count_of_smtp': smtp_all_count,
        'count_imap_valid': imap_valid_count,
        'count_imap_invalid': imap_invalid_count,
        'smtp_checked': smtp_checked,
        'imap_checked': imap_checked
    }
    return JsonResponse(data)


@api_view(['GET', 'POST'])
@login_required(login_url='users:login')
@require_http_methods(["GET", "POST"])
def panel_table_placeholder(request):
    """
    Renders the tables view template with table data.
    
    This view function handles both GET and POST requests and requires user authentication.    
    Returns rendered tables template with active page context set to 'tables'.
    """
    return render(request, 'tables.html', {'active_page': "tables"})


@api_view(['GET', 'POST'])
@login_required(login_url='users:login')
@require_http_methods(["GET", "POST"])
def panel_settings(request):
    """
    Renders the settings view template with settings data.
    
    This view function handles both GET and POST requests and requires user authentication.    
    Returns rendered settings template with active page context set to 'settings'.
    """
    return render(request, 'settings.html', {'active_page': "settings"})


api_view(['POST'])
@csrf_exempt
def upload_file_by_url(request):
    """
    Handles file upload via URL endpoint.    

    Downloads file from provided URL and saves it to appropriate directory based on country.
    Returns JSON response with status and filename or error details.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        file_url = data.get('url')

        if not file_url:
            return JsonResponse({'status': 404, 'error': 'No URL provided'}, status=404)

        try:
            response = requests.get(file_url)
            if response.status_code == 200:
                filename = os.path.basename(file_url).replace(" ", "_")
                country = extract_country_from_filename(filename)

                if country:
                    save_path = os.path.join('app', 'data', 'combofiles', country)
                else:
                    save_path = os.path.join('app', 'data', 'combofiles')

                os.makedirs(save_path, exist_ok=True)

                filepath = os.path.join(save_path, filename)
                with open(filepath, 'wb') as file:
                    file.write(response.content)

                return JsonResponse({'status': 200, 'filename': filename})

            else:
                return JsonResponse({'status': 404, 'error': 'File not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 500, 'error': str(e)}, status=500)
    else:
        return JsonResponse({'status': 405, 'error': 'Method not allowed'}, status=405)
    

@api_view(['GET'])
@require_GET
async def check_smtp_view(request):
    """
    Async view to check SMTP emails from database.

    Creates an event loop and runs the check_smtp_emails_from_db task.
    Returns redirect to home on success or error response on failure.
    """
    try:
        loop = asyncio.get_event_loop()
        await loop.create_task(check_smtp_emails_from_db())
        return redirect('/')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@require_GET
async def check_imap_view(request):
    """
    Async view to check IMAP emails from database.
    
    Creates an event loop and runs the check_imap_emails_from_db task.
    Returns redirect to home on success or error response on failure.
    """
    try:
        loop = asyncio.get_event_loop()
        await loop.create_task(check_imap_emails_from_db())
        return redirect('/')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

@api_view(['GET'])
async def parse_messages(client, channel):
    """
    Parses messages from a Telegram channel using the provided client.

    Retrieves the last 10 messages and extracts sender, date, and text.
    Returns a list of message dictionaries with formatted data.
    """
    messages = []
    async for message in client.iter_messages(channel, limit=10):
        messages.append({
            'sender': message.sender_id,
            'date': message.date.strftime('%Y-%m-%d %H:%M:%S'),
            'text': message.text
        })
    return messages


@api_view(['GET'])
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


@api_view(['POST'])
async def write_messages(filename, messages):
    """
    Writes messages to a JSON file asynchronously.
    
    Takes a filename and messages list as input parameters.
    Saves the messages with proper UTF-8 encoding and indentation.
    """
    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(messages, ensure_ascii=False, indent=4))


@api_view(['GET'])
async def read_logs(ind):
    """
    Reads SMTP and IMAP logs from temp log files.
    
    Creates empty log files if they don't exist.
    Returns the last 100 lines of logs starting from the given index.
    """
    smtp_log_path = os.path.join("app", "data", "temp_logs", 'temp_smtp.log')
    imap_log_path = os.path.join("app", "data", "temp_logs", 'temp_imap.log')

    if not os.path.exists(smtp_log_path):
        async with aiofiles.open(smtp_log_path, 'w') as smtp_file:
            await smtp_file.write('')

    if not os.path.exists(imap_log_path):
        async with aiofiles.open(imap_log_path, 'w') as imap_file:
            await imap_file.write('')

    async with aiofiles.open(smtp_log_path, 'r') as smtp_file, aiofiles.open(imap_log_path, 'r') as imap_file:
        smtp_lines = await smtp_file.readlines()
        imap_lines = await imap_file.readlines()

    smtp_logs = list(map(lambda line: line.strip(), smtp_lines))[ind:ind + 100]
    imap_logs = list(map(lambda line: line.strip(), imap_lines))[ind:ind + 100]

    return JsonResponse({"smtp_logs": smtp_logs, "imap_logs": imap_logs, "n": len(smtp_logs)})


@api_view(['GET'])
async def get_logs(request):
    """
    Reads SMTP and IMAP logs from temp log files.
    
    Returns logs starting from index 0.
    Returns a JSON response containing the logs.
    """
    # logs = await read_logs(ind)
    logs = await read_logs(0)
    return JsonResponse({"logs": logs})


@api_view(['POST'])
async def clear_temp_logs(request):
    """
    Clears the temporary SMTP and IMAP log files.
    
    Creates empty log files if they don't exist.
    Returns a JSON response indicating success or failure.
    """
    smtp_log_path = os.path.join("app", "data", "temp_logs", 'temp_smtp.log')
    imap_log_path = os.path.join("app", "data", "temp_logs", 'temp_imap.log')

    try:
        if os.path.exists(smtp_log_path):
            async with aiofiles.open(smtp_log_path, 'w') as smtp_file:
                await smtp_file.write('')
        if os.path.exists(imap_log_path):
            async with aiofiles.open(imap_log_path, 'w') as imap_file:
                await imap_file.write('')
        return JsonResponse({"message": "Logs cleared successfully"}, status=200)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)
    

@api_view(['GET'])
@require_GET
def clear_full_logs(request):
    """
    Clears the full SMTP and IMAP log files.
    
    Removes the log files from the filesystem if they exist.
    Returns a JSON response indicating success or failure.
    """
    smtp_log_path = os.path.join(settings.BASE_DIR, "app", "data", "temp_logs", 'smtp.log')
    imap_log_path = os.path.join(settings.BASE_DIR, "app", "data", "temp_logs", 'imap.log')

    try:
        os.remove(smtp_log_path)
        os.remove(imap_log_path)
        return JsonResponse({"message": "Logs cleared successfully"}, status=200)
    except FileNotFoundError:
        return JsonResponse({"message": "Log files not found"}, status=404)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)


@api_view(['POST'])
def remove_duplicate_lines(file_path):
    """
    Removes duplicate lines from a text file while preserving the original encoding.

    Uses MIME type detection to ensure only text files are processed.
    Returns the number of duplicate lines that were removed.
    """
    try:
        # Determine file type
        mime_type = mimetypes.guess_type(file_path)[0]
        if not mime_type or not mime_type.startswith("text"):
            raise ValueError("Invalid file type. Only text files are supported for removing duplicates.")

        # Detect file encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            detection = chardet.detect(raw_data)
            encoding = detection.get('encoding', 'utf-8')  # Default to 'utf-8'

            if encoding is None:
                raise ValueError("Unable to detect file encoding")

            # Read file lines with detected encoding
            lines = raw_data.decode(encoding).splitlines()

        # Remove duplicate lines
        unique_lines = list(set(lines))

        # Rewrite file with unique lines using same encoding
        with open(file_path, 'w', encoding=encoding) as f:
            f.write('\n'.join(unique_lines))

        # Return number of removed lines
        return len(lines) - len(unique_lines)
    except Exception as e:
        logging.error(f"Error removing duplicate lines: {e}")
        raise
    

@api_view(['GET'])
@require_GET
def download_logs_file(request):
    """
    Downloads SMTP and IMAP log files as a zip archive.

    Creates a temporary zip file containing the logs from the data/full_logs directory.
    Returns a FileResponse with the zip file for download, then removes the temporary file.
    """
    directory = os.path.join(settings.BASE_DIR, 'data', 'full_logs')
    files_to_zip = ["smtp.log", "imap.log"]
    zip_filename = os.path.join(settings.BASE_DIR, 'full_logs.zip')

    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file in files_to_zip:
            file_path = os.path.join(directory, file)
            if os.path.exists(file_path):
                zipf.write(file_path, os.path.basename(file_path))

    try:
        response = FileResponse(open(zip_filename, 'rb'), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename={os.path.basename(zip_filename)}'
        return response
    finally:
        os.remove(zip_filename)
        

@api_view(['GET'])
@require_GET
def check_smtp_emails_route(request):
    """
    Checks SMTP emails from the database asynchronously.
    
    Returns a JSON response with the results of the SMTP checks.
    Handles any errors and returns a 500 status code if an exception occurs.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        tasks = [
            asyncio.ensure_future(check_smtp_emails_from_db())
        ]
        smtp_results = loop.run_until_complete(asyncio.gather(*tasks))
        result = {'smtp_results': smtp_results}
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    finally:
        loop.close()
        

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

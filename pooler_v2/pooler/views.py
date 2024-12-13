import asyncio
import io
import json
import logging
import os

import zipfile

import chardet
import aiofiles
import requests
from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from .pooler_logging import logger_temp_smtp
from .utils import extract_country_from_filename, chunks, get_email_bd_data, check_smtp_emails_from_db, \
    check_smtp_emails_from_zip
from files.models import ExtractedData
import mimetypes
from django.urls import reverse_lazy
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


logger = logging.getLogger(__name__)



# @require_http_methods(['GET', 'POST'])
# def login(request):
#     if request.method == 'POST':
#         username = request.POST['username']
#         password = request.POST['password']
#         user = authenticate(request, username=username, password=password)
#         if user is not None:
#             login(request, user)
#             return redirect('panel') #redirect to panel
#         else:
#             return HttpResponse("Invalid credentials", status=401)
#
#     return render(request, "signin.html") #render login page


@require_http_methods(["GET"])
def redirect_to_panel(request):
    return redirect(reverse_lazy('pooler:panel'))


@login_required(login_url='users:login')
@require_http_methods(["GET", "POST"])
def panel(request):
    return render(request, 'index.html', {'active_page': "dashboard"})


@login_required(login_url='users:login')
@require_http_methods(["GET", "POST"])
def panel_table_placeholder(request):
    return render(request, 'tables.html', {'active_page': "tables"})


@login_required(login_url='users:login')
@require_http_methods(["GET", "POST"])
def panel_settings(request):
    return render(request, 'settings.html', {'active_page': "settings"})



@csrf_exempt
def upload_file_by_url(request):
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




@require_GET
async def check_emails_view(request, filename):
    try:
        smtp_results, imap_results = await asyncio.gather(
            check_smtp_emails_from_zip(filename),
            check_imap_emails(filename)
        )
        result = {'smtp_results': smtp_results, 'imap_results': imap_results}
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


async def parse_messages(client, channel):
    messages = []
    async for message in client.iter_messages(channel, limit=10):
        messages.append({
            'sender': message.sender_id,
            'date': message.date.strftime('%Y-%m-%d %H:%M:%S'),
            'text': message.text
        })
    return messages


async def read_existing_messages(filename):
    if os.path.exists(filename):
        async with aiofiles.open(filename, 'r', encoding='utf-8') as f:
            content = await f.read()
            return json.loads(content) if content else []
    return []


async def write_messages(filename, messages):
    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(messages, ensure_ascii=False, indent=4))


async def read_logs(ind):
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


async def get_logs(request, ind):
    logs = await read_logs(ind)
    return logs


async def clear_temp_logs(request):
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


@require_GET
def clear_full_logs(request):
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



def remove_duplicate_lines(file_path):
    try:
        # Определяем тип файла
        mime_type = mimetypes.guess_type(file_path)[0]
        if not mime_type or not mime_type.startswith("text"):
            raise ValueError("Invalid file type. Only text files are supported for removing duplicates.")

        # Определяем кодировку файла
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            detection = chardet.detect(raw_data)
            encoding = detection.get('encoding', 'utf-8')  # По умолчанию 'utf-8'

            if encoding is None:
                raise ValueError("Unable to detect file encoding")

            # Читаем строки файла в указанной кодировке
            lines = raw_data.decode(encoding).splitlines()

        # Убираем дубликаты строк
        unique_lines = list(set(lines))

        # Перезаписываем файл уникальными строками в той же кодировке
        with open(file_path, 'w', encoding=encoding) as f:
            f.write('\n'.join(unique_lines))

        # Возвращаем количество удалённых строк
        return len(lines) - len(unique_lines)
    except Exception as e:
        logging.error(f"Error removing duplicate lines: {e}")
        raise



@require_GET
def download_logs_file(request):
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


@require_GET
def check_smtp_emails_route(request):
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




# async def check_imap_emails(filename):
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
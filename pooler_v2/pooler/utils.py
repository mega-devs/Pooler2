import asyncio
import hashlib
import imaplib
import io
import json
import os
import random
import zipfile
import string
from datetime import datetime, timedelta
from django.db import IntegrityError
# from .models import EmailCheck
import aiofiles
import aioimaplib
import aiosmtplib
from files.models import ExtractedData
from asyncio import gather
import re
import smtplib

import dns.resolver

from files.service import logger
from root import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


#
# class SmtpDriver:
#     """
#     A class to handle SMTP connection checking.
#
#     Methods:
#         check_connection(email, password): Checks the SMTP connection for a given email and password.
#     """

# async def check_connection(self, email, password):
#     """
#     Check the SMTP connection for a given email and password.
#
#     Args:
#         email (str): Email address to check.
#         password (str): Password for the email address.
#
#     Returns:
#         dict: Connection status and port information.
#     """
#     try:
#         # Load SMTP service and port configurations
#         async with aiofiles.open(os.path.join('app', 'static', 'json', 'inc_smtpservices.json'), 'r') as f:
#             content = await f.read()
#             smtp_services = json.loads(content)
#
#         async with aiofiles.open(os.path.join('app', 'static', 'json', 'inc_smtpports.json'), 'r') as f:
#             content = await f.read()
#             smtp_ports = json.loads(content)['smtpports']
#
#         email_domain = email.split('@')[1]
#         host = smtp_services["smtpservices"].get(email_domain, None)
#
#         if not host:
#             raise ValueError(f"No SMTP service found for domain: {email_domain}")
#
#         for port in smtp_ports:
#             smtp_server = aiosmtplib.SMTP(hostname=host.split(':')[0], port=port, start_tls=True, timeout=10)
#             try:
#                 print(f"[SMTP] Trying {host}:{port}")
#                 await smtp_server.connect()
#                 await smtp_server.login(email, password)
#                 await smtp_server.quit()
#
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
#
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


# Function to check if a datetime object is recent
def is_recent(self, last_active: datetime) -> bool:
    if last_active is None:
        return False
    return last_active > (datetime.now() - timedelta(hours=1))


# Function to compute the MD5 hash of a string
def md5(plaintext: str):
    return hashlib.md5(plaintext.encode('utf-8')).hexdigest()


# Function to generate a random string of a given length
def gen_rand_string(n: int):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))


def extract_country_from_filename(filename):
    match = re.search(r'(?<=_)([A-Z]{2})(?=[_\W])', filename)
    if match:
        return match.group(1)
    return None


def remove_duplicate_lines(file_path):
    print(f"Removing duplicates from file: {file_path}")
    try:
        with open(file_path, 'r', errors='ignore') as file:
            lines = file.readlines()

        unique_lines = set(lines)
        num_duplicates = len(lines) - len(unique_lines)

        with open(file_path, 'w', errors='ignore') as file:
            file.writelines(unique_lines)

        if num_duplicates > 0:
            base_name, extension = os.path.splitext(file_path)
            new_file_path = f"{base_name}_{len(unique_lines)}{extension}"
            os.rename(file_path, new_file_path)
        return num_duplicates
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return 0


def get_email_bd_data():
    emails_data = []
    data = ExtractedData.objects.all()
    for el in data:
        emails_data.append({'smtp_server': el['provider'], 'email': el['email'], 'password': el['password']})
    return emails_data


# Function to validate an IMAP server
def imapCheck(email, password, imapServerName, port):
    try:
        M = imaplib.IMAP4_SSL(imapServerName)
        M.login(email, password)
        return True
    except Exception as e:
        logger.debug('e')
        return False


async def process_chunk_from_file(chunk, results):
    """Программа проверяет почтовый адрес на валидность и SMTP и IMAP сразу по написанию, по наличию МХ записей на
    сервере и по
    привествию с сервера, данные о почтовых адресах загружены из зип архива."""
    for cred in chunk:
        if "@" not in cred:
            continue
        if cred.count(":") != 1:
            continue

        server, data = cred.strip().split(":")
        port, email, password = data.split(",")
        smtp_status = 'invalid'

        try:
            match = re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', email)
            if match:
                try:
                    records = dns.resolver.resolve("mail.ru", 'MX')
                    mx_record = records[0].exchange
                    mx_record = str(mx_record)
                    if mx_record is not None:
                        server = smtplib.SMTP()
                        server.set_debuglevel(0)

                        try:
                            server.connect(mx_record)
                            code, message = server.helo(server)
                            if server[0:4] == 'smtp':
                                server = smtplib.SMTP(server, port)
                                if code == 250:
                                    smtp_status = 'valid'
                            elif server[0:4] == 'imap':
                                check_result = imapCheck(email, password, server, port)
                                if check_result:
                                    imap_status = 'valid'
                                else:
                                    imap_status = 'invalid'
                        except Exception as ex:
                            print(ex)
                except Exception as ex:
                    print(ex)
                result = {'email': email, 'password': password, 'status': smtp_status, 'imap_status': imap_status}
                results.append(result)
            # status = await driver.check_connection(email, password)
            # if status == 'valid':
            #     results.append(status)

            logger.info({'email': email,
                         'password': password,
                         'smtp_valid': smtp_status,
                         'imap_valid': imap_status,
                         'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

        except Exception as e:
            logger.error(f"Error checking connection for email {email}: {e}")


async def process_chunk_from_db(chunk, smtp_results):
    """Так же проверяет почтовые адреса на валидность SMTP, но данные загружены из бд."""
    status = 'invalid'

    email = chunk['email']
    name, server = email.split('@')
    smtp_server = 'smtp.' + server
    imap_server = 'imap.' + server

    password = chunk['password']

    try:
        match = re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', email)
        if match:
            try:
                records = dns.resolver.resolve("mail.ru", 'MX')
                mx_record = records[0].exchange
                mx_record = str(mx_record)
                if mx_record is not None:
                    server = smtplib.SMTP()
                    server.set_debuglevel(0)

                    try:
                        server.connect(mx_record)
                        code, message = server.helo(smtp_server)
                        server = smtplib.SMTP(smtp_server, 587)
                        if code == 250:
                            status = True
                    except Exception as ex:
                        print(ex)
            except Exception as ex:
                print(ex)

        smtp_result = {'email': email, 'password': password, 'status': status}
        smtp_results.append(smtp_result)
        # status = await driver.check_connection(email, password)
        # if status == 'valid':
        #     results.append(status)

        logger.info({'email': email,
                     'password': password,
                     'valid': status,
                     'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

    except Exception as e:
        logger.error(f"Error checking connection for email {email}: {e}")


async def imap_process_chunk_from_db(chunk, imap_results):
    """Так же проверяет почтовые адреса на валидность IMAP, но данные загружены из бд."""
    email = chunk['email']
    name, server = email.split('@')
    imap_server = 'imap.' + server

    password = chunk['password']

    try:
        match = re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', email)
        if match:
            try:
                records = dns.resolver.resolve("mail.ru", 'MX')
                mx_record = records[0].exchange
                mx_record = str(mx_record)
                if mx_record is not None:
                    try:
                        imap_check_result = imapCheck(email, password, imap_server, 993)
                        if imap_check_result:
                            imap_status = 'valid'
                        else:
                            imap_status = 'invalid'
                    except Exception as ex:
                        print(ex)
            except Exception as ex:
                print(ex)

        imap_result = {'email': email, 'password': password, 'status': imap_status}
        imap_results.append(imap_result)
        # status = await driver.check_connection(email, password)
        # if status == 'valid':
        #     results.append(status)

        logger.info({'email': email,
                     'password': password,
                     'valid': imap_status,
                     'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

    except Exception as e:
        logger.error(f"Error checking connection for email {email}: {e}")


async def check_smtp_imap_emails_from_zip(filename):
    '''Основная функция проверки почтовых адресов по smtp и imap, в ней реализована работа с архивом и далее данные
    передаются на функцию process_chunk_from_file результатом является добавление значений в записи в базе данных по
    соответствующим почтовым адресам.'''
    # smtp_driver = SmtpDriver()
    results =[]

    file_path = os.path.join(settings.MEDIA_ROOT, "combofiles", filename)

    if filename.endswith('.zip'):
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            for zip_info in zip_file.infolist():
                if not zip_info.is_dir():
                    with io.TextIOWrapper(zip_file.open(zip_info), encoding='utf-8') as f:
                        lines = f.readlines()
                        chunk_size = 100
                        chunked_lines = list(chunks(lines, chunk_size))
                        tasks = [process_chunk_from_file(chunk, results) for chunk in
                                 chunked_lines]
                        await gather(*tasks)
    else:
        async with aiofiles.open(file_path, 'r') as f:
            lines = await f.readlines()
            chunk_size = 100
            chunked_lines = list(chunks(lines, chunk_size))
            tasks = [process_chunk_from_file(chunk, results) for chunk in chunked_lines]
            await gather(*tasks)

    for el in results:
        ExtractedData.objects.filter(email=el['email']).update(smtp_is_valid=el['status'], imap_is_valid=el[
            'imap_status'])


async def check_smtp_emails_from_db(filename):
    '''Основная функция проверки почтовых адресов SMTP, запускает подфункцию process_chunk_from_db'''
    # smtp_driver = SmtpDriver()
    smtp_results = []

    data = get_email_bd_data()

    tasks = [process_chunk_from_db(el, smtp_results) for el in
             data]
    await gather(*tasks)

    for el in smtp_results:
        ExtractedData.objects.filter(email=el['email']).update(smtp_is_valid=el['status'])


async def check_imap_emails_from_db(filename):
    '''Основная функция, запускает подфункцию imap_process_chank from_db'''
    # smtp_driver = SmtpDriver()
    imap_results = []

    data = get_email_bd_data()

    tasks = [process_chunk_from_db(el, imap_results) for el in
             data]
    await gather(*tasks)

    for el in imap_results:
        ExtractedData.objects.filter(email=el['email']).update(imap_is_valid=el['status'])
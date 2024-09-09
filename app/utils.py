import hashlib
import json
import os
import re
import random
import string
import aiofiles
import aioimaplib
import aiosmtplib

from datetime import datetime, timedelta


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


class SmtpDriver:
    async def check_connection(self, email, password):
        try:
            async with aiofiles.open(os.path.join('app', 'static', 'json', 'inc_smtpservices.json'), 'r') as f:
                content = await f.read()
                data = json.loads(content)
                email_domain = email.split('@')[1]

                async with aiofiles.open(os.path.join('app', 'static', 'json', 'inc_smtpports.json'), 'r') as f:
                    content = await f.read()
                    smtp_ports = json.loads(content)['smtpports']

                for port in smtp_ports:
                    host = data["smtpservices"][email_domain].split(':')[0]
                    smtp_server = aiosmtplib.SMTP(hostname=host, port=port, start_tls=True, timeout=10)
                    try:
                        print(f"[SMTP] Trying {host}:{port}")
                        await smtp_server.connect()
                        await smtp_server.login(email, password)
                        await smtp_server.quit()
                        return {'status': 'valid', 'port': port}
                    except aiosmtplib.SMTPAuthenticationError as e:
                        print(f"[SMTP] {str(e)}")
                        await smtp_server.quit()
                    except Exception as e:
                        print(f"[SMTP] {str(e)}")
                        pass
                return {'status': 'dead'}
        except Exception as e:
            print(f"[SMTP] {str(e)}")
            return {'status': 'dead'}


class ImapDriver:
    async def check_connection(self, email, password):
        try:
            async with aiofiles.open(os.path.join('app', 'static', 'json', 'inc_imapservices.json'), 'r') as f:
                content = await f.read()
                data = json.loads(content)
                email_domain = email.split('@')[1]

                async with aiofiles.open(os.path.join('app', 'static', 'json', 'inc_imapports.json'), 'r') as f:
                    content = await f.read()
                    imap_ports = json.loads(content)['imapports']

                for port in imap_ports:
                    host = data["imapservices"][email_domain].split(':')[0]
                    imap_server = aioimaplib.IMAP4_SSL(host, port, timeout=10)
                    try:
                        print(f"[IMAP] Trying {host}:{port}")
                        await imap_server.wait_hello_from_server()
                        response = await imap_server.login(email, password)
                        await imap_server.logout()
                        if response.result == "OK":
                            return {'status': 'valid', 'port': port}
                    except aioimaplib.AioImapException as e:
                        print(f"[IMAP] {str(e)}")
                        await imap_server.close()
                    except Exception as e:
                        print(f"[IMAP] {str(e)}")
                        pass
                return {'status': 'dead'}
        except Exception as e:
            print(f"[IMAP] {str(e)}")
            return {'status': 'dead'}


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

# Function to validate an SMTP server

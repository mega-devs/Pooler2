import hashlib
import json
import os
import random
import re
import string
from datetime import datetime, timedelta
from django.db import IntegrityError
from .models import EmailCheck
import aiofiles
import aioimaplib
import aiosmtplib


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

    async def check_connection(self, email, password):
        """
        Check the SMTP connection for a given email and password.

        Args:
            email (str): Email address to check.
            password (str): Password for the email address.

        Returns:
            dict: Connection status and port information.
        """
        try:
            # Load SMTP service and port configurations
            async with aiofiles.open(os.path.join('app', 'static', 'json', 'inc_smtpservices.json'), 'r') as f:
                content = await f.read()
                smtp_services = json.loads(content)

            async with aiofiles.open(os.path.join('app', 'static', 'json', 'inc_smtpports.json'), 'r') as f:
                content = await f.read()
                smtp_ports = json.loads(content)['smtpports']

            email_domain = email.split('@')[1]
            host = smtp_services["smtpservices"].get(email_domain, None)

            if not host:
                raise ValueError(f"No SMTP service found for domain: {email_domain}")

            for port in smtp_ports:
                smtp_server = aiosmtplib.SMTP(hostname=host.split(':')[0], port=port, start_tls=True, timeout=10)
                try:
                    print(f"[SMTP] Trying {host}:{port}")
                    await smtp_server.connect()
                    await smtp_server.login(email, password)
                    await smtp_server.quit()

                    # Save result to the database
                    EmailCheck.objects.create(
                        email=email,
                        status='valid',
                        check_type='SMTP',
                    )
                    return {'status': 'valid', 'port': port}
                except aiosmtplib.SMTPAuthenticationError:
                    await smtp_server.quit()
                except Exception as e:
                    print(f"[SMTP] {str(e)}")
                    pass

            # If all ports fail
            EmailCheck.objects.create(
                email=email,
                status='invalid',
                check_type='SMTP',
            )
            return {'status': 'invalid'}
        except Exception as e:
            # Save error to the database
            try:
                EmailCheck.objects.create(
                    email=email,
                    status='error',
                    check_type='SMTP',
                )
            except IntegrityError:
                pass  # Ignore if email already exists in the database
            return {'status': 'error', 'error': str(e)}


class ImapDriver:
    """
    A class to handle IMAP connection checking.

    Methods:
        check_connection(email, password): Checks the IMAP connection for a given email and password.
    """

    async def check_connection(self, email, password):
        """
        Check the IMAP connection for a given email and password.

        Args:
            email (str): Email address to check.
            password (str): Password for the email address.

        Returns:
            dict: Connection status and port information.
        """
        try:
            # Load IMAP service and port configurations
            async with aiofiles.open(os.path.join('app', 'static', 'json', 'inc_imapservices.json'), 'r') as f:
                content = await f.read()
                imap_services = json.loads(content)

            async with aiofiles.open(os.path.join('app', 'static', 'json', 'inc_imapports.json'), 'r') as f:
                content = await f.read()
                imap_ports = json.loads(content)['imapports']

            email_domain = email.split('@')[1]
            host = imap_services["imapservices"].get(email_domain, None)

            if not host:
                raise ValueError(f"No IMAP service found for domain: {email_domain}")

            for port in imap_ports:
                imap_server = aioimaplib.IMAP4_SSL(host, port, timeout=10)
                try:
                    print(f"[IMAP] Trying {host}:{port}")
                    await imap_server.wait_hello_from_server()
                    response = await imap_server.login(email, password)
                    await imap_server.logout()
                    if response.result == "OK":
                        # Save result to the database
                        EmailCheck.objects.create(
                            email=email,
                            status='valid',
                            check_type='IMAP',
                        )
                        return {'status': 'valid', 'port': port}
                except aioimaplib.AioImapException:
                    await imap_server.close()
                except Exception as e:
                    print(f"[IMAP] {str(e)}")
                    pass

            # If all ports fail
            EmailCheck.objects.create(
                email=email,
                status='invalid',
                check_type='IMAP',
            )
            return {'status': 'invalid'}
        except Exception as e:
            # Save error to the database
            try:
                EmailCheck.objects.create(
                    email=email,
                    status='error',
                    check_type='IMAP',
                )
            except IntegrityError:
                pass  # Ignore if email already exists in the database
            return {'status': 'error', 'error': str(e)}


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


def is_valid_telegram_username(username):
    return re.match(r'^(https://t\.me/|@)?[a-zA-Z0-9_]{5,32}$', username)

# Function to validate an SMTP server

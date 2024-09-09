import os
import queue
import multiprocessing as mp
import sys
import utils
import imaplib
import email
from multiprocessing.managers import ListProxy
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from manage import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# IMAPConfig dataclass definition
@dataclass
class IMAPConfig:
    server: str
    port: int
    email: str
    password: str
    valid: Optional[bool] = None
    last_checked: Optional[datetime] = None

    def __str__(self):
        return f"{self.server}:{self.port}:{self.email}:{self.password}"

    def __hash__(self):
        return hash((self.server, self.port, self.email))


# IMAPProcessor class definition
class IMAPProcessor:
    def __init__(self):
        # Initialize control check signal and yet_to_add_imaps queue
        self.control_check_signal = False
        self.yet_to_add_imaps = queue.Queue()

        # Create IMAP database and load IMAP configurations into memory
        self.__create_imap_db()
        self.__load_imap_db_into_memory()

        # Start a new process for adding IMAP configurations to the database
        self.P_add_imaps_to_db = mp.Process(target=self.__add_imaps_to_db)
        self.P_add_imaps_to_db.start()

    # Method to toggle the control check signal
    def toggle_signal(self, new_control_check_signal: bool) -> bool:
        self.control_check_signal = new_control_check_signal
        return new_control_check_signal

    # Method to fetch the control check signal
    def fetch_signal(self):
        return self.control_check_signal

    # Method to create the IMAP database (already done)
    def __create_imap_db(self):
        pass

    # Method to load IMAP configurations from the database into memory
    def __load_imap_db_into_memory(self):
        with app.app_context():
            from app.models import IMAP

            imaps = IMAP.query.all()
            existing_maps = set(shared_imaps)
            for imap in imaps:
                imap_config = IMAPConfig(imap.server, imap.port, imap.email, imap.password, imap.valid,
                                         imap.last_checked)
                if imap_config not in existing_maps:
                    shared_imaps.append(imap_config)

    # Method to continuously add IMAP configurations to the database
    def __add_imaps_to_db(self):
        with app.app_context():
            from app import db
            from app.models import IMAP

            while True:
                try:
                    imap = self.yet_to_add_imaps.get()
                    if not IMAP.query.filter_by(server=imap.server, port=imap.port, email=imap.email).count():
                        shared_imaps.append(imap)
                        db.session.add(
                            IMAP(
                                server=imap.server,
                                port=imap.port,
                                email=imap.email,
                                password=imap.password,
                                valid=imap.valid,
                                last_checked=imap.last_checked
                            )
                        )
                        db.session.commit()
                    self.yet_to_add_imaps.task_done()
                except Exception as e:
                    pass

    # Method to push a list of IMAP configurations to the processing queue
    def __push_imaps_to_queue(self, imaps: List[IMAPConfig]):
        for imap in imaps:
            self.yet_to_add_imaps.put(imap)

    # Method to convert a list of lines into a list of IMAPConfig objects
    def __lines_to_imaps(self, lines: List[str]) -> List[IMAPConfig]:
        imaps = []
        for line in lines:
            server, port, email, password = line.split(':', 3)
            imaps.append(IMAPConfig(server, int(port), email, password))
        return imaps

    # Method to add a list of lines as IMAP configurations to the processing queue
    def add_lines(self, lines: List[str]):
        self.__push_imaps_to_queue(self.__lines_to_imaps(lines))

    # Method to connect to an IMAP server and fetch emails
    def fetch_emails(self, imap_config: IMAPConfig):
        mail = imaplib.IMAP4_SSL(imap_config.server, imap_config.port)
        mail.login(imap_config.email, imap_config.password)
        mail.select("inbox")

        result, data = mail.uid('search', None, "ALL")
        email_ids = data[0].split()
        emails = []
        for id in email_ids:
            result, email_data = mail.uid('fetch', id, '(BODY.PEEK[])')
            raw_email = email_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            emails.append(email_message)

        return emails

    # def poll_imap_servers(self):
    #     while True:
    #         for imap_config in shared_imaps:
    #             emails = self.fetch_emails(imap_config)
    #             # Process emails as needed
    #             for email in emails:
    #                 # Do something with the email, like saving it to the database or sending a notification
    #                 pass
    #         time.sleep(60)  # Wait for 60 seconds before polling again


# Shared list of IMAP configurations
shared_imaps: ListProxy[IMAPConfig] = utils.manager.list()
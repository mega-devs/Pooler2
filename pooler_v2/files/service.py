import os
import zipfile



def handle_archive(file_path, save_path):
    try:
        with zipfile.ZipFile(file_path, 'r') as archive:
            archive.extractall(save_path)
        os.remove(file_path)
    except zipfile.BadZipFile:
        raise ValueError("Invalid archive format")


def determine_origin(filename):
    if "smtp" in filename.lower():
        return "SMTP"
    elif "imap" in filename.lower():
        return "IMAP"
    elif "telegram" in filename.lower():
        return "TELEGRAM"
    else:
        return "MANUAL"
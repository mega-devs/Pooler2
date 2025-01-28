import asyncio
import os
from pathlib import Path
import subprocess

from files.models import ExtractedData
from pooler.utils import get_email_bd_data, process_chunk_from_db

from celery import app

from root import settings


@app.shared_task
def run_selected_tests(test_files=None):
    """
    Run selected pytest scripts based on relative paths.
    If no test_files are specified, all tests will run.
    """
    try:
        command = ["pytest", "--disable-warnings"]
        
        # Convert relative paths to absolute paths
        base_dir = settings.BASE_DIR.parent  # Adjust as needed
        absolute_paths = []
        if test_files:
            absolute_paths = [os.path.join(base_dir, test_file) for test_file in test_files]

        command.extend(absolute_paths)

        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return {
            "stdout": process.stdout,
            "stderr": process.stderr,
            "returncode": process.returncode,
        }
    except Exception as e:
        return {"error": str(e)}


@app.shared_task
def check_imap_emails_from_db():
    '''Main function that runs the sub-function imap_process_chunk from db'''
    imap_results = []

    data = get_email_bd_data()
    tasks = [process_chunk_from_db(el, imap_results) for el in data]

    asyncio.run(async_gather(tasks))

    for el in imap_results:
        ExtractedData.objects.filter(email=el['email']).update(imap_is_valid= True if el['status'] == 'VALID' else None if el['status'] == 'INVALID' else False)


@app.shared_task
def check_smtp_emails_from_db():
    '''Main function for checking SMTP email addresses, launches process_chunk_from_db subfunction'''
    smtp_results = []
    data = get_email_bd_data()

    tasks = [process_chunk_from_db(el, smtp_results) for el in
             data]
    asyncio.run(async_gather(tasks))

    for el in smtp_results:
        ExtractedData.objects.filter(email=el['email']).update(smtp_is_valid= True if el['status'] == 'VALID' else None if el['status'] == 'INVALID' else False)


async def async_gather(tasks):
    await asyncio.gather(*tasks)

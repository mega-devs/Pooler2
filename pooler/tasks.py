import asyncio
import os
from pathlib import Path
import subprocess

from files.models import ExtractedData
from pooler.utils import get_email_bd_data, process_chunk_from_db

from celery import app

from root import settings

from django.db import transaction


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


@app.shared_task(queue="long_running_tasks")
def check_imap_emails_from_db():
    """Runs the IMAP email check process asynchronously without blocking Celery workers."""
    imap_results = []

    # Fetch email data
    data = get_email_bd_data()

    # Run async function using event loop in a non-blocking way
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def async_task_runner():
        tasks = [process_chunk_from_db(el, imap_results) for el in data]
        await asyncio.gather(*tasks)

    loop.run_until_complete(async_task_runner())
    
    bulk_updates = []
    for el in imap_results:
        status = el['status']
        is_valid = True if status == 'VALID' else None if status == 'INVALID' else False
        bulk_updates.append(ExtractedData(email=el['email'], imap_is_valid=is_valid))
    if bulk_updates:
        ExtractedData.objects.bulk_update(bulk_updates, ['imap_is_valid'])  # Bulk update for performance



@app.shared_task(queue="long_running_tasks")
async def check_smtp_emails_from_db():
    """Main function for checking SMTP email addresses asynchronously."""
    
    smtp_results = []
    data = get_email_bd_data()

    tasks = [process_chunk_from_db(el, smtp_results) for el in data]
    await asyncio.gather(*tasks)

    update_list = []
    for el in smtp_results:
        email_obj = ExtractedData.objects.get(email=el['email'])
        email_obj.smtp_is_valid = True if el['status'] == 'VALID' else None if el['status'] == 'INVALID' else False
        update_list.append(email_obj)

    if update_list:
        with transaction.atomic():  # Ensure efficient bulk updates
            ExtractedData.objects.bulk_update(update_list, ['smtp_is_valid'])

async def async_gather(tasks):
    await asyncio.gather(*tasks)

import asyncio

from files.models import ExtractedData
from pooler.utils import get_email_bd_data, process_chunk_from_db

from celery import app


@app.shared_task
def check_imap_emails_from_db():
    '''Main function that runs the sub-function imap_process_chunk from db'''
    imap_results = []

    data = get_email_bd_data()
    tasks = [process_chunk_from_db(el, imap_results) for el in data]

    asyncio.run(async_gather(tasks))

    for el in imap_results:
        ExtractedData.objects.filter(email=el['email']).update(imap_is_valid=el['status'])


@app.shared_task
def check_smtp_emails_from_db():
    '''Main function for checking SMTP email addresses, launches process_chunk_from_db subfunction'''
    smtp_results = []
    data = get_email_bd_data()

    tasks = [process_chunk_from_db(el, smtp_results) for el in
             data]
    asyncio.run(async_gather(tasks))

    for el in smtp_results:
        ExtractedData.objects.filter(email=el['email']).update(smtp_is_valid=el['status'])


async def async_gather(tasks):
    await asyncio.gather(*tasks)

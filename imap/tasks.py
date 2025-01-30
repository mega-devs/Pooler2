from celery import shared_task

import logging

from imap.checker.MailRipV3_NOGUI import checker, targets_total, hits, fails
from imap.models import ImapConfig


logger = logging.getLogger(__name__)


@shared_task
def check_imap(user_id, file_content):
    config = ImapConfig.objects.filter(user_id=user_id).first()

    rounds = 1

    if config:
        default_timeout = config.timeout
        default_threads = config.threads
        rounds = config.rounds

    else:
        default_timeout = 5
        default_threads = 5

    combofile = file_content

    for _ in range(rounds):
        try:
            checker(
                default_threads,
                default_timeout,
                combofile,
                user_id
            )
        except Exception as e:
            logger.error(f"Error in check_imap: {e}")

    return {
        "combos": targets_total,
        "hits": hits,
        "fails": fails
    }

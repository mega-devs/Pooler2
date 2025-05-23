from celery import shared_task

import logging

from smtp.checker.MailRipV3_NOGUI import checker, targets_total, hits, fails
from smtp.models import SmtpConfig


logger = logging.getLogger(__name__)


@shared_task
def check_smtp(user_id, file_content):
    config = SmtpConfig.objects.filter(user_id=user_id)

    if config:
        default_timeout = config.timeout
        default_threads = config.threads
    else:
        default_timeout = 5
        default_threads = 5

    combofile = file_content

    try:
        checker(
            default_threads,
            default_timeout,
            combofile,
            user_id
        )
    except Exception as e:
        logger.error(f"Error in check_smtp: {e}")

    return {
        "combos": targets_total,
        "hits": hits,
        "fails": fails
    }

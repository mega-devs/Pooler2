from celery import shared_task

from imap.checker.MailRipV3_NOGUI import checker, targets_total, hits, fails
from imap.models import ImapConfig


@shared_task
def check_imap(user_id, file_content):
    config = ImapConfig.objects.filter(user_id=user_id)

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
        return {"status": f"failed, raised exception: {e}"}

    return {
        "combos": targets_total,
        "hits": hits,
        "fails": fails
    }

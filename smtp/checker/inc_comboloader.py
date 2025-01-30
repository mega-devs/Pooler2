from ..models import SMTPCheckResult, SMTPCombo, SMTPStatistics
from .inc_etc import email_verification, blacklist_check


def comboloader(file_content, user_id):
    '''
    Loads combos from a given string.

    :param str file_content: string containing the combos
    :param user: user object for saving check results
    :return: list with loaded combos
    '''

    loaded_combos = set()
    failed_combos = []
    total_combos = 0

    for line in file_content.splitlines():

        new_combo = line.strip().replace(';', ':').replace(',', ':').replace('|', ':')
        parts = new_combo.split(':')

        if len(parts) < 2:
            continue

        total_combos += 1

        email, password = parts[0], parts[1]

        if not (email_verification(email) and not blacklist_check(email)):
            failed_combos.append((email, password, 'fail'))
            continue

        if new_combo not in loaded_combos:
            loaded_combos.add(new_combo)
            SMTPCombo.objects.get_or_create(email=email, password=password, user_id=user_id)

    for email, password, status in failed_combos:
        combo, created = SMTPCombo.objects.get_or_create(email=email, password=password, user_id=user_id)
        SMTPCheckResult.objects.create(combo=combo, user_id=user_id, status=status)

    stats, created = SMTPStatistics.objects.get_or_create(user_id=user_id)
    stats.total_combos += total_combos
    stats.total_fails += len(failed_combos)
    stats.save()

    return list(loaded_combos)


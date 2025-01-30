import sys
from datetime import datetime
from inc_etc import result
from inc_etc import email_verification
from inc_etc import blacklist_check

def comboloader(input_file):
    '''
    Loads combos from a given file.

    :param str input_file: file containing the combos
    :return: list with loaded combos
    '''
    loaded_combos = []
    output_blacklist = str('combos_blacklisted')
    output_clean = str('combos_loaded')
    timestamp = datetime.now()
    output_startup = str(
        'Comboloader started on: '
        + str(timestamp.strftime('%Y-%m-%d %H:%M:%S'))
        + f', combofile: {input_file}'
    )
    result(output_blacklist, str('\n' + output_startup + '\n' + len(output_startup)*'='))
    result(output_clean, str('\n' + output_startup + '\n' + len(output_startup) * '='))
    try:
        for line in open(input_file, 'r'):
            try:
                new_combo = str(
                    line.replace(';', ':').replace(',', ':').replace('|', ':')
                )
                with_email = email_verification(
                    new_combo.split(':')[0]
                )
                if with_email == False:
                    continue
                blacklisted = blacklist_check(
                    new_combo.split(':')[0]
                )
                if blacklisted == True:
                    new_combo = str(new_combo.replace('\n', ''))
                    result(output_blacklist,new_combo)
                    continue
                if new_combo in loaded_combos:
                    continue
                else:
                    loaded_combos.append(new_combo)
                    new_combo = str(new_combo.replace('\n', ''))
                    result(output_clean, new_combo)
            except:
                continue
        result(output_blacklist, str(f'\nCombos imported from file: {input_file}.\n=== END OF IMPORT ==='))
        result(output_clean, str(f'\nCombos imported from file: {input_file}.\n=== END OF IMPORT ==='))
    except:
        result(output_blacklist, str(f'\nAn error occurred while importing the combos from file: {input_file}.\n=== END OF IMPORT ==='))
        result(output_clean, str(f'\nAn error occurred while importing the combos from file: {input_file}.\n=== END OF IMPORT ==='))
    return loaded_combos


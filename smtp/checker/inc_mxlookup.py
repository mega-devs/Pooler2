import sys
import socket
import dns.resolver
from .inc_etc import domain_verification

def get_host(default_timeout, email):
    '''
    Checks the DNS records of an email-domain for MX infos and returns any found SMTP URI.

    :param float default_timeout: connection timeout
    :param str email: email with domain to check
    :return: found (True, False), smtp_host (SMTP URI)
    '''
    socket.setdefaulttimeout(default_timeout)
    found = False
    smtp_host = str('none')
    smtp_domain = str(email.split('@')[1])
    get_records = dns.resolver.Resolver(configure=False)
    get_records.nameservers = ['8.8.8.8']
    records = get_records.resolve(smtp_domain, 'MX')
    counter = 0
    while found == False:
        try:
            possible_host = str(records[counter]).split(' ')[1].rstrip('.')
            verify_domain = domain_verification(possible_host)
            if verify_domain == True:
                smtp_host = possible_host
                found = True
            else:
                counter += 1
        except:
            break
    return found, smtp_host

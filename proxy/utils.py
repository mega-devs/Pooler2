from datetime import datetime

from proxy.checker import ProxyChecker


def check_single_proxy(proxy):

    checker = ProxyChecker()

    if proxy.username and proxy.password:
        response = checker.check_proxy(f'{proxy.host}:{proxy.port}', user=proxy.username, password=proxy.password)
    else:
        response = checker.check_proxy(f'{proxy.host}:{proxy.port}')
    if not response:
        proxy.is_active = False
    elif proxy.is_active is None or not proxy.is_active:
        proxy.country = response['country']
        proxy.is_active = True
        proxy.country_code = response['country_code']
        proxy.anonymity = response['anonymity']
        proxy.timeout = response['timeout']
    proxy.last_time_checked = datetime.now()
    proxy.save()
    return proxy

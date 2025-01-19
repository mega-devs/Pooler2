import datetime

from celery import app
from .checker import ProxyChecker

from .models import Proxy


from concurrent.futures import ThreadPoolExecutor, as_completed


@app.shared_task
def check_proxy_health():
    checker = ProxyChecker()
    proxies = Proxy.objects.all()

    def check_and_update(proxy):
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
        proxy.last_time_checked = datetime.datetime.now()
        proxy.save()
        return proxy

    with ThreadPoolExecutor(max_workers=100) as executor:
        future_to_proxy = {executor.submit(check_and_update, proxy): proxy for proxy in proxies}
        for future in as_completed(future_to_proxy):
            proxy = future_to_proxy[future]
            try:
                future.result()
            except Exception as e:
                print(f'Error checking proxy {proxy.host}:{proxy.port} - {e}')

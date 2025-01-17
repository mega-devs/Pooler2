from concurrent.futures import ThreadPoolExecutor

from celery import app
import asyncio
from proxy_checker import ProxyChecker

from .models import Proxy


@app.shared_task
def check_proxy_health():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_check_proxy_help())


async def async_check_proxy_help():
    checker = ProxyChecker()
    proxies = Proxy.objects.all()

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        for proxy in proxies:
            response = await loop.run_in_executor(executor, checker.check_proxy, f'{proxy.host}:{proxy.port}')
            if not response:
                proxy.is_active = False
                proxy.save()
            elif proxy.is_actve is None:
                proxy.country = response['country']
                proxy.is_active = True
                proxy.country_code = response['country_code']
                proxy.anonymity = response['anonymity']
                proxy.timeout = response['timeout']
                proxy.save()

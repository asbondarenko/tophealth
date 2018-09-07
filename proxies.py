import asyncio
import random

from contextlib import suppress

import proxybroker


class AsyncProxyFinder:
    def __init__(self):
        self.__alive_proxies = set()
        self.__proxies = asyncio.Queue()
        self.__broker = proxybroker.Broker(self.__proxies)

    async def update_proxies(self):
        asyncio.ensure_future(self.__broker.find(types=['HTTP'], limit=100))
        while True:
            proxy = await self.__proxies.get()
            if proxy is None:
                asyncio.ensure_future(self.__broker.find(types=['HTTP'], limit=100))
            self.__alive_proxies.add(f'http://{proxy.host}:{proxy.port}')

    async def get(self):
        while len(self.__alive_proxies) == 0:
            await asyncio.sleep(10)
        proxy_address, = random.sample(self.__alive_proxies, 1)
        return proxy_address

    async def remove(self, proxy_address):
        with suppress(KeyError):
            self.__alive_proxies.remove(proxy_address)

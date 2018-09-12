import asyncio
import random

from contextlib import suppress

import proxybroker


class AsyncProxyFinder:
    def __init__(self):
        self.__alive_proxies = set()
        self.__proxies = asyncio.Queue()
        self.__broker = proxybroker.Broker(self.__proxies)

    async def update_proxies(self, min_count=1000):
        print("Fetching proxies...")
        await self.__broker.find(types=['HTTP'], limit=min_count * 2)
        while True:
            proxy = await self.__proxies.get()
            if proxy is None:
                while len(self.__alive_proxies) > min_count:
                    await asyncio.sleep(10)

                print("Fetching proxies...")
                await self.__broker.find(types=['HTTP'], limit=min_count * 2)
            else:
                proxy_address = f'http://{proxy.host}:{proxy.port}'
                self.__alive_proxies.add(proxy_address)

    async def get(self):
        while True:
            if len(self.__alive_proxies) > 0:
                proxy_address, = random.sample(self.__alive_proxies, 1)
                return proxy_address

            print('Waiting for proxies...')
            await asyncio.sleep(10)

            while len(self.__alive_proxies) == 0:
                print('<!> No proxies available')
                await asyncio.sleep(10)

    async def remove(self, proxy_address):
        with suppress(KeyError):
            self.__alive_proxies.remove(proxy_address)

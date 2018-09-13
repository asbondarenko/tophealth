import asyncio
import random

from contextlib import suppress

import proxybroker


class AsyncProxyFinder:
    def __init__(self):
        self.__alive_proxies = set()
        self.__proxies = asyncio.Queue()
        self.__broker = None
        self.__task = None

    async def run_proxy_broker(self, limit):
        if self.__broker is not None:
            self.__proxies = asyncio.Queue()
            self.__broker.stop()

        self.__broker = proxybroker.Broker(self.__proxies)

        # ---- PROXYBROKER BUG BYPASS ----
        from proxybroker import resolver
        setattr(getattr(self.__broker, '_resolver'), '_ip_hosts', getattr(resolver.Resolver, '_ip_hosts').copy())
        # ---- PROXYBROKER BUG BYPASS ----

        print("Fetching proxies...")
        asyncio.ensure_future(self.__broker.find(types=['HTTP'], limit=limit))

    async def update_proxies(self, min_count=150):
        await self.run_proxy_broker(min_count * 2)
        while True:
            try:
                need_to_restart_broker = True
                for _ in range(2):
                    if self.__proxies.empty():
                        await asyncio.sleep(10)
                    else:
                        need_to_restart_broker = False
                        break

                if need_to_restart_broker:
                    print("Proxies query is empty!")
                    await self.run_proxy_broker(min_count * 2)
                else:
                    proxy = await self.__proxies.get()
                    if proxy is None:

                        while len(self.__alive_proxies) > min_count:
                            await asyncio.sleep(10)

                        await self.run_proxy_broker(min_count * 2)
                    else:
                        proxy_address = f'http://{proxy.host}:{proxy.port}'
                        print("Append proxy:", proxy_address)
                        self.__alive_proxies.add(proxy_address)

            except Exception as ex:
                await self.run_proxy_broker(min_count * 2)
                print(ex)

    async def get(self):
        while True:
            if len(self.__alive_proxies) > 0:
                proxy_address, = random.sample(self.__alive_proxies, 1)
                return proxy_address

            await asyncio.sleep(10)
            while len(self.__alive_proxies) == 0:
                await asyncio.sleep(10)

    async def remove(self, proxy_address):
        with suppress(KeyError):
            self.__alive_proxies.remove(proxy_address)

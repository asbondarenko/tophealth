import asyncio
import random

import proxybroker


class AsyncProxyFinder:
    def __init__(self):
        self.__work_proxies = dict()
        self.__dead_proxies = set()
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

        proxy_count = len(self.__work_proxies)
        print(f"Fetching proxies({proxy_count}/{limit})...")
        asyncio.ensure_future(self.__broker.find(types=['HTTP'], limit=limit))

    async def update_proxies(self, min_count=10):
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
                        while len(self.__work_proxies) > min_count:
                            await asyncio.sleep(10)

                        await self.run_proxy_broker(min_count * 2)
                    else:
                        proxy_address = f'http://{proxy.host}:{proxy.port}'
                        if proxy_address not in self.__work_proxies:
                            await self.report(proxy_address, failed=False)

            except Exception as ex:
                await self.run_proxy_broker(min_count * 2)
                print(ex)

    async def get(self):
        while True:
            try:
                proxy_address, = random.sample(self.__work_proxies.keys(), 1)
                return proxy_address
            except ValueError:
                await asyncio.sleep(10)
                while len(self.__work_proxies) == 0:
                    await asyncio.sleep(10)

    async def report(self, proxy_address, failed: bool):
        if proxy_address in self.__dead_proxies:
            return

        cumulative, count = self.__work_proxies.get(proxy_address, (0, 0))
        cumulative += 1 if not failed else -1
        count += 1

        self.__work_proxies[proxy_address] = (cumulative, count)
        if failed and count > 10 and (cumulative / count) < 0.5:
            print(f"<!> Dead proxy {proxy_address}")
            del self.__work_proxies[proxy_address]
            self.__dead_proxies.add(proxy_address)

import argparse
import asyncio
import random
import traceback

import aiohttp
from api_client import ScraperAPI
import scrapers

from proxies import AsyncProxyFinder


PROXY_ERRORS = (
    aiohttp.client_exceptions.ClientProxyConnectionError,
    aiohttp.client_exceptions.ClientHttpProxyError,
    aiohttp.client_exceptions.ServerDisconnectedError,
    aiohttp.client_exceptions.ClientOSError,
    aiohttp.client_exceptions.ClientResponseError,
    asyncio.TimeoutError
)


async def execute_tasks(tasks, proxies, semaphore):
    user_agent = 'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) ' \
                 'AppleWebKit/537.36 (KHTML, like Gecko) ' \
                 'Chrome/51.0.2704.64 Safari/537.36 '

    async with aiohttp.ClientSession(headers={'User-Agent': user_agent}) as session:
        while True:
            async with semaphore:
                if len(tasks) == 0:
                    break
                attempts, task = tasks.pop(random.randint(1, len(tasks)) - 1)

            proxy_address = await proxies.get()
            try:
                await task(session, proxy_address)
                await proxies.report(proxy_address, failed=False)

            # Try again if proxy is not working
            except PROXY_ERRORS:
                await proxies.report(proxy_address, failed=True)
                async with semaphore:
                    tasks.append((attempts - 0.1, task))

            # Try again and print the error
            except Exception as ex:
                if attempts > 0:
                    tasks.append((attempts - 1, task))
                traceback.print_exc()
                print(ex, task)


async def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='mode')
    subparsers.add_parser('init')

    scrape_parser = subparsers.add_parser('scrape')
    scrape_parser.add_argument('--source', nargs='+', choices=list(scrapers.SCRAPER_SOURCES))
    scrape_parser.add_argument('--city', nargs='+', help="City for scraping")
    scrape_parser.add_argument('--region', nargs='+', help="Region for scraping")
    scrape_parser.add_argument('--country', nargs='+', help="Country for scraping")
    scrape_parser.add_argument('--service', nargs='+', help="List of services")

    review_parser = subparsers.add_parser('review')
    review_parser.add_argument('--source', nargs='+', choices=list(scrapers.REVIEWS_SOURCES))
    review_parser.add_argument('--city', nargs='+', help="City for scraping")
    review_parser.add_argument('--region', nargs='+', help="Region for scraping")
    review_parser.add_argument('--country', nargs='+', help="Country for scraping")
    review_parser.add_argument('--service', nargs='+', help="List of services")

    args = parser.parse_args()

    filter_source = list(set(args.source or [])) or None
    filter_city = list(set(args.city or [])) or None
    filter_region = list(set(args.region or [])) or None
    filter_country = list(set(args.country or [])) or None
    filter_services = list(set(args.service or [])) or None

    # todo: Change api address
    api_address = None
    api = ScraperAPI(api_address)
    proxies = AsyncProxyFinder()

    semaphore = asyncio.Semaphore()
    tasks = []

    async def task_factory(partial_constructor):
        async with semaphore:
            maximum_attempts = 10
            tasks.append((maximum_attempts, partial_constructor(
                api=api,
                task_factory=task_factory
            )))

    if args.mode == 'scrape':
        for source, scraper in scrapers.SCRAPER_SOURCES.items():
            if filter_source is not None and source not in filter_source:
                continue

            services = await api.get_services(source, filter_services)
            locations = await api.get_locations(source, filter_city, filter_region, filter_country)

            for country in locations:
                for region in country['regions']:
                    for city in region['cities']:
                        for service in services:
                            await task_factory(lambda **kwargs: scraper(
                                service=service,
                                country={
                                    'name': country['name'],
                                    'code': country['code']
                                },
                                region={
                                    'name': region['name'],
                                    'code': region['code']
                                },
                                city=city,
                                **kwargs
                            ))

    if args.mode == 'review':
        for source, scraper in scrapers.REVIEWS_SOURCES.items():
            if filter_source is not None and source not in filter_source:
                continue

            services = await api.get_services(source, filter_services)
            locations = await api.get_locations(source, filter_city, filter_region, filter_country)

            for country in locations:
                for region in country['regions']:
                    for city in region['cities']:
                        for service in services:
                            facilities = await api.get_facilities(service['id'], city['id'])
                            print(facilities)

                            if len(facilities) > 0:
                                await task_factory(lambda **kwargs: scraper(
                                    service=service,
                                    country={
                                        'name': country['name'],
                                        'code': country['code']
                                    },
                                    region={
                                        'name': region['name'],
                                        'code': region['code']
                                    },
                                    city=city,
                                    facilities=facilities,
                                    **kwargs
                                ))

    if len(tasks) > 0:
        worker_count = 20
        asyncio.ensure_future(proxies.update_proxies())
        await asyncio.gather(*(execute_tasks(tasks, proxies, semaphore) for _ in range(worker_count)))


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

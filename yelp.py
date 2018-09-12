import asyncio
import json
import random
import traceback
from pprint import pprint
from urllib.parse import urljoin
import urllib.parse

import aiohttp
import bs4

from proxies import AsyncProxyFinder


def validate(page):
    if page.select_one('.y-container_content--maintenance') is not None:
        raise PermissionError('Yelp access error. Need to use another proxy')

    if page.select_one('form[name="captcha_form"]') is not None:
        raise PermissionError('Yelp access error. Need to use another proxy')

    return page


async def search_task(session, proxy_address, page_url):
    async with session.get(page_url, proxy=proxy_address, timeout=10) as response:
        page = validate(bs4.BeautifulSoup(await response.text(), 'html.parser'))

        for media_clinic in page.select('span.indexed-biz-name'):
            clinic_link = media_clinic.select_one('a')
            yield 'task', {
                'type': 'extract',
                'url': urljoin(page_url, clinic_link.attrs.get('href'))
            }


async def extract_task(session, proxy_address, page_url):
    async with session.get(page_url, proxy=proxy_address, timeout=10) as response:
        page = validate(bs4.BeautifulSoup(await response.text(), 'html.parser'))

        json_script = page.select_one('script[type="application/ld+json"]')
        if json_script is None:
            with open('wrong_json.html', 'w') as f:
                f.write(page.prettify())

        json_text = json_script.text
        json_data = json.JSONDecoder(strict=False).decode(json_text)

        # Business Name
        name_element = page.select_one('h1.biz-page-title')
        if name_element is None:
            return
        name = str.strip(name_element.text)

        # Business Logo URL
        logo = json_data["image"]

        # Business Website URL
        website_element = page.select_one('span.biz-website a')
        website = website_element.text if website_element is not None else None

        # Business Address
        address_element = page.select_one('span[itemprop="streetAddress"]')
        if address_element is None:
            return
        address = str.strip(address_element.text)

        # Business City
        city_name_element = page.select_one('span[itemprop="addressLocality"]')
        if city_name_element is None:
            return
        city_name = str.strip(city_name_element.text)

        # Business Region
        region_name_element = page.select_one('span[itemprop="addressRegion"]')
        if region_name_element is None:
            return
        region_name = str.strip(region_name_element.text)

        # Business Phone Number
        phone = json_data['telephone']

        # About the Business
        about = []
        about_part = None
        for about_element in page.select('.from-biz-owner-content > *'):
            if about_element.name == 'h3':
                if 'specialties' in about_element.text.lower():
                    about_part = 'specialties'
                else:
                    about_part = None

            elif about_part is not None:
                about_text = about_element.text.strip()
                if len(about_text) > 0:
                    about.append(about_text)

        categories = []
        for category in page.select('.biz-page-header .category-str-list a'):
            categories.append(str.strip(category.text))

        rating = {
            'count': 0,
            'stars': 0
        }
        if 'aggregateRating' in json_data:
            rating = {
                'count': json_data['aggregateRating']['reviewCount'],
                'stars': json_data['aggregateRating']['ratingValue']
            }

        yield 'result', {
            'categories': categories,
            'location': {
                'region': {
                    'code': region_name
                },
                'city': city_name,
            },
            'name': name,
            'logo': logo,
            'phone': phone,
            'website': website,
            'address': address,

            'about': '\n'.join(about),

            'rating': rating
        }


async def start_tasks(proxy_manager, start_task):
    task_attempts = 10

    statistic = {
        'done': 0,
        'count': 1
    }
    tasks = [(task_attempts, start_task)]

    async def handle_message(message, content):
        if message == 'task':
            statistic['count'] += 1
            tasks.append((task_attempts, content))

        if message == 'result':
            yield content

    user_agent = 'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64' \
                 ' Safari/537.36'

    async with aiohttp.ClientSession(headers={'User-Agent': user_agent}) as session:
        while len(tasks) > 0:
            attempts, task = tasks.pop(random.randint(1, len(tasks)) - 1)
            proxy_address = await proxy_manager.get()
            try:
                if task['type'] == 'search':
                    async for response in search_task(session, proxy_address, task['url']):
                        async for result in handle_message(*response):
                            yield result

                if task['type'] == 'extract':
                    async for response in extract_task(session, proxy_address, task['url']):
                        async for result in handle_message(*response):
                            yield result

                print('done', task)
                statistic['done'] += 1

            except (aiohttp.client_exceptions.ClientProxyConnectionError,
                    aiohttp.client_exceptions.ClientHttpProxyError,
                    aiohttp.client_exceptions.ServerDisconnectedError,
                    aiohttp.client_exceptions.ClientOSError,
                    aiohttp.client_exceptions.ClientResponseError,
                    asyncio.TimeoutError,
                    PermissionError):
                await proxy_manager.remove(proxy_address)
                tasks.append((attempts - task_attempts / 10, task))

            except Exception as ex:
                if attempts > 0:
                    tasks.append((attempts - 1, task))
                traceback.print_exc()
                print(ex, task)

        print(f"statistic: {statistic['done']}/{statistic['count']}", start_task)


async def scrape(proxy_manager, callback, country, region, city, category):
    category = category['name']
    country = country['code']
    region = region['name']
    city = city['name']

    task = {
        'type': 'search',
        'url': 'https://www.yelp.com/search?find_desc='
               f'{urllib.parse.quote(category)}&find_loc='
               f'{urllib.parse.quote(city)},+'
               f'{urllib.parse.quote(region)},+'
               f'{urllib.parse.quote(country)}'
               '&sortby=rating'
    }

    async for facility in start_tasks(proxy_manager, task):
        await callback(facility)


async def main():
    async def print_business(business):
        pprint(business)

    proxy_finder = AsyncProxyFinder()
    asyncio.ensure_future(proxy_finder.update_proxies())

    await scrape(
        callback=print_business,
        proxy_manager=proxy_finder,

        category={
            'name': 'Acupuncture',
        },
        country={
            'name': 'Canada',
            'code': 'CA'
        },
        region={
            'name': 'Ontario',
            'code': 'ON'
        },
        city={
            'name': 'Toronto'
        }
    )


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

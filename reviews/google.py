import asyncio
import random
import traceback
from pprint import pprint
import urllib.parse

import aiohttp
import bs4
import re


async def match_task(session, task):
    async with session.get(task['url']) as response:
        page = bs4.BeautifulSoup(await response.text(), 'html.parser')

        clinic_name = page.select_one('.xpdopen .kp-header [role="heading"] span')
        if clinic_name is None:
            return

        rating_stars_element = page.select_one('div span.rtng')
        if rating_stars_element is None:
            return

        rating_stars = float(rating_stars_element.text.replace(',', '.'))

        rating_count_element = page.select_one('div span.rtng ~ span a span')
        if rating_stars_element is None:
            return

        rating_count = int(re.sub('[^\d]*', '', rating_count_element.text))

        yield 'result', {
            'facility_name': task['clinic_name'],
            'stars': rating_stars,
            'count': rating_count,
        }


async def start_tasks(init_tasks):
    task_attempts = 10
    tasks = [
        (task_attempts, task)
        for task in init_tasks
    ]

    async def handle_message(message, content):
        if message == 'task':
            tasks.append((task_attempts, content))

        if message == 'result':
            yield content

    handler = {
        'search': match_task
    }

    user_agent = 'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64' \
                 ' Safari/537.36'
    async with aiohttp.ClientSession(headers={'User-Agent': user_agent}) as session:
        while len(tasks) > 0:
            attempts, task = tasks.pop(random.randint(1, len(tasks)) - 1)

            try:
                async for response in handler[task['type']](session, task):
                    async for result in handle_message(*response):
                        yield result

                print('done', task)

            except Exception as ex:
                if attempts > 0:
                    tasks.append((attempts - 1, task))
                await asyncio.sleep(2)
                traceback.print_exc()
                print(ex, task)


async def scrape_reviews(callback, country, region, city, category, clinic_names):
    region = str.lower(region['name'])
    city = str.lower(city['name'])

    tasks = [
        {
            'type': 'search',
            'url': f'https://www.google.com/search?q=' + urllib.parse.quote(f'{region}, {city}, {clinic_name}'),
            'clinic_name': clinic_name
        }
        for clinic_name in clinic_names
    ]
    async for result in start_tasks(tasks):
        await callback(result)


async def main():
    async def print_business(business):
        pprint(business)

    await scrape_reviews(
        callback=print_business,

        category={
            'name': 'physiotherapists',
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
        },
        clinic_names=[
            'Absolute Health Centre',
            'High Performance Sports Medicine'
        ]
    )

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

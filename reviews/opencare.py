import asyncio
import random
import traceback
from pprint import pprint
from urllib.parse import urljoin

import aiohttp
import bs4


async def match_task(session, task):
    async with session.get(task['url']) as response:
        page = bs4.BeautifulSoup(await response.text(), 'html.parser')

        with open('response.html', 'w') as f:
            f.write(page.prettify())

        for media_info in page.select('.media-body .col-info'):
            clinic_link = media_info.select_one('h4 a')
            clinic_name = clinic_link.text
            if clinic_name in task['clinics']:
                rating_count_element = media_info.select_one('address + * .text-muted')
                if rating_count_element is not None:
                    rating_stars = len(media_info.select('.fa-star')) + len(media_info.select('.fa-star-half-o')) / 2
                    rating_count = int(rating_count_element.text.strip('()'))
                    yield 'result', {
                        'facility_name': clinic_name,
                        'stars': rating_stars,
                        'count': rating_count,
                    }


async def extract_task(session, task):
    print('WOOOOOOW!!!!!!!!!!')
    print('WOOOOOOW!!!!!!!!!!')
    print('WOOOOOOW!!!!!!!!!!')
    print('WOOOOOOW!!!!!!!!!!')
    print('WOOOOOOW!!!!!!!!!!')
    print('WOOOOOOW!!!!!!!!!!')
    async with session.get(task['url']) as response:
        page = bs4.BeautifulSoup(await response.text(), 'html.parser')


async def start_tasks(start_task):
    task_attempts = 10
    tasks = [(task_attempts, start_task)]

    async def handle_message(message, content):
        if message == 'task':
            tasks.append((task_attempts, content))

        if message == 'result':
            yield content

    handler = {
        'match': match_task,
        'extract': extract_task
    }
    async with aiohttp.ClientSession() as session:
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
    region = str.lower(region['code'])
    city = str.lower(city['name'])
    category = str.lower(category['name'])

    task = {
        'type': 'match',
        'url': f'https://www.opencare.com/{category}/{city}-{region}/',
        'clinics': set(clinic_names)
    }
    async for result in start_tasks(task):
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

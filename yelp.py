import asyncio
import json
import os
import random
import re
import string
from pprint import pprint

import arsenic
import arsenic.errors
from arsenic.browsers import Chrome
from arsenic.services import Chromedriver

from bs4 import BeautifulSoup


class BrowserFactory:
    def __init__(self, headless=True, proxy_address=None, disable_images=False, windows_size=(1200, 600)):
        options = {
            'args': [
                'disable-gpu',
                'allow-running-insecure-content',
                'no-referrers',
                'ignore-certificate-errors',
                'disk-cache-dir=' + os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache"),
                'disk-cache-size=41943040',
            ],
        }
        if headless:
            options["args"].append("headless")

        if proxy_address is not None:
            if isinstance(proxy_address, tuple):
                options["args"].append('proxy-server=%s:%d' % proxy_address)
            elif isinstance(proxy_address, str):
                options["args"].append('proxy-server=' + proxy_address)

        if windows_size is not None:
            if isinstance(windows_size, tuple):
                options["args"].append('window-size=%d,%d' % windows_size)
            elif isinstance(windows_size, str):
                options["args"].append('window-size=' + windows_size)

        if disable_images:
            options["prefs"] = {
                'profile': {
                    'default_content_setting_values': {
                        'images': 2
                    }
                }
            }

        self.options = options

    def __call__(self):
        service = Chromedriver()
        browser = Chrome(chromeOptions=self.options)
        return arsenic.get_session(service, browser)


async def extract_info(session, url):
    await session.get(url)
    page_source = await session.get_page_source()
    page = BeautifulSoup(page_source, features="html.parser")

    json_text = page.select_one('script[type="application/ld+json"]').text
    json_data = json.JSONDecoder(strict=False).decode(json_text)

    # Business Name
    try:
        name_element = await session.get_element('h1.biz-page-title')
        name = await name_element.get_text()
    except arsenic.errors.NoSuchElement:
        name = None

    # Business Logo URL
    try:
        logo_element = await session.get_element('[itemprop="image"]')
        logo = await logo_element.get_attribute('content')
    except arsenic.errors.NoSuchElement:
        logo = None

    # Business Website URL
    try:
        website_element = await session.get_element('span.biz-website a')
        website = await website_element.get_text()
    except arsenic.errors.NoSuchElement:
        website = None

    # Business Address Street
    street_element = page.select_one('span[itemprop="streetAddress"]')
    if street_element is not None:
        street = street_element.text
    else:
        street = None

    # Business Address Locality
    city_element = page.select_one('span[itemprop="addressLocality"]')
    if city_element is not None:
        city = city_element.text
    else:
        city = None

    # Business Address Region
    region_element = page.select_one('span[itemprop="addressRegion"]')
    if region_element is not None:
        region = region_element.text
    else:
        region = None

    # Business Phone Number
    if json_data is not None:
        phone = 'tel:' + json_data.get('telephone')
    else:
        phone = None

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

    # Reviews Rating
    if 'aggregateRating' in json_data:
        stars = json_data['aggregateRating']['ratingValue']
    else:
        stars = None

    # Reviews Sources
    if 'reviewCount' in json_data:
        reviews = json_data['reviewCount']
    else:
        reviews = 0

    yield 'business', {
        'name': name,
        'logo': logo,
        'website': website,
        'region': region,
        'city': city,
        'street': street,
        'about': '\n'.join(about),
        'phone': phone,
        'rating': {
            'stars': stars,
            'reviews': reviews
        }
    }


async def search_clinics(session, url):
    await session.get(url)
    # todo: ensure that page is correct without network error, captcha or something else

    for media_clinic in await session.get_elements('span.indexed-biz-name'):
        clinic_link = await media_clinic.get_element('a')
        yield 'task', {
            'type': 'extract',
            'url': await clinic_link.get_attribute('href')
        }


async def start_tasks(start_task):
    tasks = [start_task]

    new_session = BrowserFactory(
        headless=True,
        disable_images=True
    )

    async def handle_message(message, content):
        if message == 'task':
            tasks.append(content)

        elif message == 'business':
            yield content

        else:
            raise NotImplementedError

    async with new_session() as session:
        while len(tasks) > 0:
            task = tasks.pop(random.randint(1, len(tasks)) - 1)

            if task['type'] == 'search':
                async for response in search_clinics(session, task['url']):
                    async for result in handle_message(*response):
                        yield result

            elif task['type'] == 'extract':
                async for response in extract_info(session, task['url']):
                    async for result in handle_message(*response):
                        yield result

            else:
                raise NotImplementedError


async def scrape(callback, region, city, category):
    region = region['name']
    city = city['name']
    category = category['name']

    task = {
        'type': 'search',
        'url': f'https://www.yelp.com/search?find_desc={category}&find_loc={city},+{region}&sortby=rating&start=0'
    }
    async for business in start_tasks(task):
        business.update({
            'city': city,
            'region': region,
            'category': category
        })
        await callback(business)


async def main():
    async def print_business(business):
        pprint(business)

    await scrape(print_business, 'ontario', 'toronto', 'chiropractors')
    # await scrape(print_business, 'new-york', 'new-york', 'chiropractors')


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

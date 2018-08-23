import asyncio
import os
import random
import string
from pprint import pprint

import arsenic
import arsenic.errors
from arsenic.browsers import Chrome
from arsenic.services import Chromedriver


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

    # Business Name
    try:
        name_element = await session.get_element('h1[itemprop="name"]')
        name = await name_element.get_text()
    except arsenic.errors.NoSuchElement:
        name = None

    # Business Logo URL
    try:
        logo_element = await session.get_element('meta[itemprop="image"]')
        logo = await logo_element.get_attribute('content')
    except arsenic.errors.NoSuchElement:
        logo = None

    # Business Website URL
    try:
        website_element = await session.get_element('meta[itemprop="url"]')
        website = await website_element.get_attribute('content')
    except arsenic.errors.NoSuchElement:
        website = None

    # Business Address Street
    try:
        street_element = await session.get_element('span[itemprop="streetAddress"]')
        street = await street_element.get_text()
    except arsenic.errors.NoSuchElement:
        street = None

    # Business Address Locality
    try:
        city_element = await session.get_element('span[itemprop="addressLocality"]')
        city = await city_element.get_text()
    except arsenic.errors.NoSuchElement:
        city = None

    # Business Address Region
    try:
        region_element = await session.get_element('span[itemprop="addressRegion"]')
        region = await region_element.get_text()
    except arsenic.errors.NoSuchElement:
        region = None

    # Business Phone Number
    try:
        phone_element = await session.get_element('div[data-ng-show="isShowPhoneNumber"] > a[href*="tel:"]')
        phone = await phone_element.get_attribute('href')
        if len(phone) == 0:
            phone = None
    except arsenic.errors.NoSuchElement:
        phone = None

    # About the Business
    about = []
    for panel in await session.get_elements('.panel.panel-default'):
        try:
            panel_title = await panel.get_element('h4.panel-title')
            if 'about' not in (await panel_title.get_text()).lower():
                continue
        except arsenic.errors.NoSuchElement:
            continue

        for about_parent_element in await panel.get_elements('p.ng-isolate-scope'):
            view_more = await about_parent_element.get_element(
                'a[data-ng-click*="true"][data-ng-show="isTruncated"]'
            )
            if await view_more.is_displayed():
                await view_more.click()
                about_element = await about_parent_element.get_element('span[data-ng-bind="fullText"]')
            else:
                about_element = await about_parent_element.get_element('span[data-ng-bind="truncatedText"]')

            about_text = (await about_element.get_text()).strip(string.whitespace)
            if len(about_text) > 0:
                about.append(about_text)
        break

    # Reviews Rating across x sources
    try:
        stars_element = await session.get_element('.stat-rating strong')
        stars = float(await stars_element.get_text())
    except arsenic.errors.NoSuchElement:
        stars = None

    reviews = 0
    for panel in await session.get_elements('.panel.panel-default'):
        try:
            panel_title = await panel.get_element('h4.panel-title')
            if 'reviews' not in (await panel_title.get_text()).lower():
                continue

            reviews_element = await panel_title.get_element('.hidden-xs')
            reviews = await reviews_element.get_text()
            break

        except arsenic.errors.NoSuchElement:
            continue

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

    for media_clinic in await session.get_elements('.media.media-clinic'):
        clinic_link = await media_clinic.get_element('.media-body h4 > a')
        yield 'task', {
            'type': 'extract',
            'url': await clinic_link.get_attribute('href')
        }


async def start_tasks(start_task):
    tasks = [start_task]

    new_session = BrowserFactory(
        headless=False,
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
    if (region, city, category) == ('ontario', 'toronto', 'chiropractors'):
        task = {
            'type': 'search',
            'url': 'https://www.opencare.com/chiropractors/toronto-on/'
        }
    elif (region, city, category) == ('new-york', 'new-york', 'chiropractors'):
        task = {
            'type': 'search',
            'url': 'https://www.opencare.com/chiropractors/new-york-ny/'
        }
    else:
        raise NotImplementedError

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

import html
import json
import urllib.parse
import asyncio
import aiohttp
import bs4

from scrapers.task import Task, ScrapeTask


def validate(page):
    if page.select_one('.y-container_content--maintenance') is not None:
        raise asyncio.TimeoutError('Yelp access error. Need to use another proxy')

    if page.select_one('form[name="captcha_form"]') is not None:
        raise asyncio.TimeoutError('Yelp access error. Need to use another proxy')

    return page


class ScrapeYelp(ScrapeTask):
    async def __call__(self, session, proxy_address):
        await self.task_factory(lambda **kwargs: SearchFacilityYelp(
            page_url='https://www.yelp.com/search?find_desc='
            f'{urllib.parse.quote(self.service["name"])}&find_loc='
            f'{urllib.parse.quote(self.city["name"])},+'
            f'{urllib.parse.quote(self.region["name"])},+'
            f'{urllib.parse.quote(self.country["code"])}'
            '&sortby=rating',
            **kwargs
        ))

    def __repr__(self):
        return f'create yelp task {self.service} in {self.city}'


class SearchFacilityYelp(Task):
    def __init__(self, page_url, **kwargs):
        super().__init__(**kwargs)
        self.page_url = page_url

    async def __call__(self, session: aiohttp.ClientSession, proxy_address):
        async with session.get(self.page_url, proxy=proxy_address, timeout=10) as response:
            page = validate(bs4.BeautifulSoup(await response.text(), 'html.parser'))

            for media_clinic in page.select('span.indexed-biz-name'):
                clinic_link = media_clinic.select_one('a')
                await self.task_factory(lambda **kwargs: ExtractFacilityYelp(
                    page_url=urllib.parse.urljoin(self.page_url, clinic_link.attrs.get('href')),
                    **kwargs
                ))

        print('done', self)

    def __repr__(self):
        return f"yelp.search: {self.page_url}"


class ExtractFacilityYelp(Task):
    def __init__(self, page_url, **kwargs):
        super().__init__(**kwargs)
        self.page_url = page_url

    async def __call__(self, session: aiohttp.ClientSession, proxy_address):
        async with session.get(self.page_url, proxy=proxy_address, timeout=10) as response:
            page = validate(bs4.BeautifulSoup(await response.text(), 'html.parser'))

            json_script = page.select_one('script[type="application/ld+json"]')
            json_text = json_script.text
            json_data = json.JSONDecoder(strict=False).decode(json_text)

            map_state_element = page.select_one('div[data-map-state]')
            map_state_text = map_state_element.attrs['data-map-state']
            map_state = json.JSONDecoder(strict=False).decode(html.unescape(map_state_text))

            # Geocoords
            geocoords = {'latitude': None, 'longitude': None}
            for marker in map_state['markers']:
                if marker.get('key') == 'starred_business':
                    geocoords = marker['location']

            # Postal code
            postal_code = json_data['address']['postalCode']

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
            region_code_element = page.select_one('span[itemprop="addressRegion"]')
            if region_code_element is None:
                return
            region_code = str.strip(region_code_element.text)

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

            facility_id = await self.api.post_facility(
                name=name,
                country=None,
                region={'code': region_code},
                city=city_name,
            )

            if facility_id is None:
                return

            await self.api.post_facility_info(
                facility_id=facility_id,
                source='yelp',
                about='\n'.join(about),
                logo=logo,
                phone=phone,
                website=website,
                address=address,
                geocoords=geocoords,
                postal_code=postal_code
            )

            await self.api.post_facility_reviews(
                facility_id=facility_id,
                source="yelp",
                rating=rating['stars'],
                count=rating['count']
            )

        print('done', self)

    def __repr__(self):
        return f"yelp.extract: {self.page_url}"

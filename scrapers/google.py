import asyncio
import urllib.parse

import bs4
import re

from .task import Task, ReviewTask


class ReviewGoogle(ReviewTask):
    async def __call__(self, session, proxy_address):
        for facility in self.facilities:
            await self.task_factory(lambda **kwargs: MatchGoogle(
                url='https://www.google.com/search?q=' + urllib.parse.quote(
                    f"{self.region['name']}, {self.city['name']}, {facility['name']}"
                ),
                facility=facility,
                **kwargs
            ))


def validate(page):
    if page.select_one('form#captcha-form') is not None:
        raise asyncio.TimeoutError('Google captcha error. Need to use another proxy')
    return page


class MatchGoogle(Task):
    def __init__(self, url, facility, **kwargs):
        super().__init__(**kwargs)
        self.page_url = url
        self.facility = facility

    async def __call__(self, session, proxy_address):
        async with session.get(self.page_url, proxy=proxy_address, timeout=10) as response:
            page = validate(bs4.BeautifulSoup(await response.text(), 'html.parser'))

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

        await self.api.post_facility_reviews(
            facility_id=self.facility['id'],
            source='google',
            rating=rating_stars,
            count=rating_count
        )

        for star_badge in page.select('[role="main"] .slp.f'):
            source_cite = star_badge.parent.select_one('cite')
            if source_cite is None:
                continue

            source_match = re.search(r"//[^.]+?\.([^\s]+)\.[^.]+", source_cite.text)
            if source_match is None:
                continue

            rating_match = re.search(r":[^\d]*([\d.]+)[^\d]+(\d+)", star_badge.text.replace(',', '.'))
            if rating_match is None:
                continue

            source, = source_match.groups()
            rating, count = rating_match.groups()

            print("<!>", source, 'for', self.facility['id'])

            await self.api.post_facility_reviews(
                facility_id=self.facility['id'],
                source=source,
                rating=float(rating),
                count=int(count)
            )

        print("done", self)

    def __repr__(self):
        return f'google review {self.facility["name"]} in {self.page_url}'

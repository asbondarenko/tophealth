import bs4

from .task import Task, ReviewTask


class ReviewOpencare(ReviewTask):
    async def __call__(self, session, proxy_address):
        region = str.lower(self.region['code'])
        city = str.lower(self.city['name']).replace(' ', '-')
        service = str.lower(self.service['name'])

        await self.task_factory(lambda **kwargs: MatchOpencare(
            page_url=''.join(['https://www.opencare.com/', service, '/', city, '-', region, '/']),
            facilities=self.facilities,
            **kwargs
        ))


class MatchOpencare(Task):
    def __init__(self, page_url, facilities, **kwargs):
        super().__init__(**kwargs)
        self.page_url = page_url

        # Just dict: name -> id
        self.facilities = {
            facility['name']: facility['id']
            for facility in facilities
        }

    async def __call__(self, session, proxy_address):
        async with session.get(self.page_url) as response:
            page = bs4.BeautifulSoup(await response.text(), 'html.parser')

        for media_info in page.select('.media-body .col-info'):
            clinic_link = media_info.select_one('h4 a')
            clinic_name = clinic_link.text
            if clinic_name in self.facilities:
                rating_count_element = media_info.select_one('address + * .text-muted')
                if rating_count_element is not None:
                    rating_stars = len(media_info.select('.fa-star')) + len(media_info.select('.fa-star-half-o')) / 2
                    rating_count = int(rating_count_element.text.strip('()'))

                    await self.api.post_facility_reviews(
                        facility_id=self.facilities[clinic_name],
                        source='opencare',
                        rating=rating_stars,
                        count=rating_count
                    )

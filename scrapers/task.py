from api_client import ScraperAPI


class Task:
    def __init__(self, **kwargs):
        self.api: ScraperAPI = kwargs['api']
        self.task_factory = kwargs['task_factory']

    async def __call__(self, session, proxy_address):
        raise NotImplementedError


class ScrapeTask(Task):
    def __init__(self, service, country, region, city, **kwargs):
        super().__init__(**kwargs)
        self.service = service
        self.country = country
        self.region = region
        self.city = city

    async def __call__(self, session, proxy_address):
        raise NotImplementedError


class ReviewTask(Task):
    def __init__(self, country, region, city, service, facilities, **kwargs):
        super().__init__(**kwargs)
        self.country = country
        self.region = region
        self.city = city
        self.service = service
        self.facilities = facilities

    async def __call__(self, session, proxy_address):
        raise NotImplementedError

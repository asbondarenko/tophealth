import datetime

from sqlalchemy import func, or_
import sqlalchemy.orm
import sqlalchemy.exc

import models


class ScraperAPI:
    def __init__(self, base_address):
        self.base_address = base_address

    @staticmethod
    async def __get_city(session, country, region, city):
        city_query = (
            session.query(models.City).select_from(
                sqlalchemy.join(
                    models.City,
                    sqlalchemy.join(
                        models.Region,
                        models.Country,
                        models.Region.country_id == models.Country.id
                    ),
                    models.City.region_id == models.Region.id
                )
            ).filter(
                func.lower(models.City.name) == func.lower(city),
            )
        )

        if region is not None:
            city_query = city_query.filter(or_(
                func.lower(models.Region.name) == func.lower(region.get('name')),
                func.lower(models.Region.code) == func.lower(region.get('code')),
            ))

        if country is not None:
            city_query = city_query.filter(or_(
                func.lower(models.Country.name) == func.lower(country.get('name')),
                func.lower(models.Country.code) == func.lower(country.get('code')),
            ))

        return city_query.first()

    async def post_facility(self, name, country, region, city):
        """
        :param name: Название клиники ("Back in Balance Clinic")
        :param country: {
            name: Название страны ("Canada")
            code: Код страны ("CA")
        }
        :param region: {
            name: Название региона ("Ontario")
            code: Код региона ("ON")
        }
        :param city: Название города ("Toronto")

        :return: Идентификатор клиники
        """

        if self.base_address is not None:
            raise NotImplementedError

        async with models.AsyncSession() as session:
            city_record = await self.__get_city(session, country, region, city)
            if city_record is None:
                print(f"Unknown location {{'city':{city}, 'region':{region}, 'country':{country}}}")
                return None

            facility = session.query(models.Facility).filter(
                func.lower(models.Facility.name) == func.lower(name),
                models.Facility.city_id == city_record.id
            ).first()

            if facility is None:
                facility = models.Facility(name=name, city_id=city_record.id)
                session.add(facility)
                session.commit()

            return facility.id

    async def post_facility_info(self, facility_id, source, about, logo, phone, website, address, geocoords, postal_code):
        """
        :param facility_id: Идентификатор клиники
        :param source: Источник данных ("yelp")
        :param about: Описание клиники ("We are an integrative health clinic in...")
        :param logo: URL логотипа ("https://s3-media1.fl.yelpcdn.com/bphoto/gGsNrGbKqQ5YOAW6Tmgt8w/ls.jpg")
        :param phone: ("+14166609932")
        :param website: ("backinbalanceclinic.com")

        :param address: Адрес в городе ("2 Carlton Street\nSuite 1522")
        :param geocoords: {
            latitude: (43.6616746)
            longitude: (-79.3827503)
        }
        :param postal_code: Почтовый индекс ("M5B 1J3")
        """

        if self.base_address is not None:
            raise NotImplementedError

        async with models.AsyncSession() as session:
            facility_info = session.query(models.FacilityInfo).filter(
                models.FacilityInfo.facility_id == facility_id,
                models.FacilityInfo.source == source
            ).first()

            if facility_info is None:
                facility_info = models.FacilityInfo(
                    facility_id=facility_id,
                    source=source
                )
                session.add(facility_info)

            facility_info.about = about
            facility_info.phone = phone
            facility_info.image_url = logo
            facility_info.website_url = website
            facility_info.address = address
            facility_info.fetch_date = datetime.datetime.now(datetime.timezone.utc)

            # todo: Remove the print
            print("<!>", postal_code, geocoords)

            # facility_info.geocoords = geocoords
            # facility_info.postal_code = postal_code
            try:
                session.commit()
            except sqlalchemy.exc.IntegrityError:
                session.rollback()
                raise

    async def post_facility_reviews(self, facility_id, source, rating, count):
        """
        :param facility_id: Идентификатор клиники
        :param source: Источник данных ("google")
        :param rating: Рейтинг (5.0)
        :param count: Количество отзывов (47)
        """

        if self.base_address is not None:
            raise NotImplementedError

        async with models.AsyncSession() as session:
            review = session.query(models.Review).filter(
                models.Review.facility_id == facility_id,
                models.Review.source == source
            ).first()

            if review is None:
                review = models.Review(
                    facility_id=facility_id,
                    source=source
                )
                session.add(review)

            review.rating = rating
            review.count = count

            session.commit()

    async def get_locations(self, source, filter_cities=None, filter_regions=None, filter_countries=None):
        """
        :param source: Возможно, придется по разному называть города для каждого сервиса.
        :return: {
            counties: [
                {
                    name: "Canada",
                    code: "CA",
                    regions: [
                        {
                            name: "Ontario"
                            code: "ON",
                            cities: [
                                "Toronto",
                                ...
                            ]
                        },
                        ...
                    ]
                },
                ...
            ]
        }
        Или
        :return: [
            ("Toronto", "Ontario", "ON", "Canada", "CA"),
            ("Ottawa", "Ontario", "ON", "Canada", "CA"),
            ...
        ]
        """

        if self.base_address is not None:
            raise NotImplementedError

        async with models.AsyncSession() as session:
            location_query = session.query(models.City, models.Region, models.Country).select_from(
                sqlalchemy.join(
                    models.City,
                    sqlalchemy.join(
                        models.Region,
                        models.Country,
                        models.Region.country_id == models.Country.id
                    ),
                    models.City.region_id == models.Region.id
                )
            )

            if filter_countries is not None:
                location_query = location_query.filter(sqlalchemy.or_(
                    models.Country.name.in_(filter_countries),
                    models.Country.code.in_(filter_countries),
                ))

            if filter_regions is not None:
                location_query = location_query.filter(sqlalchemy.or_(
                    models.Region.name.in_(filter_regions),
                    models.Region.code.in_(filter_regions),
                ))

            if filter_cities is not None:
                location_query = location_query.filter(
                    models.City.name.in_(filter_cities),
                )

            locations = {}
            for city, region, country in location_query.all():
                if country.id not in locations:
                    locations[country.id] = {
                        'name': country.name,
                        'code': country.code,
                        'regions': {}
                    }
                if region.id not in locations[country.id]['regions']:
                    locations[country.id]['regions'][region.id] = {
                        'name': region.name,
                        'code': region.code,
                        'cities': {}
                    }
                if city.id not in locations[country.id]['regions'][region.id]['cities']:
                    locations[country.id]['regions'][region.id]['cities'][city.id] = {
                        'name': city.name
                    }

            return [
                {
                    'id': country_id,
                    'name': country['name'],
                    'code': country['code'],
                    'regions': [
                        {
                            'id': region_id,
                            'name': region['name'],
                            'code': region['code'],
                            'cities': [
                                {
                                    'id': city_id,
                                    'name': city['name'],
                                }
                                for city_id, city in region['cities'].items()
                            ]
                        }
                        for region_id, region in country['regions'].items()
                    ]
                }
                for country_id, country in locations.items()
            ]

    async def get_services(self, source, query_categories=None):
        """
        :param query_categories:
        :param source: Название источника ("opencare").
            Для разных источников уже требуются разные названия одного и того же сервиса.
        :return: {
            "services": [
                "acupuncturists",
                "dentists",
                ...
            ]
        }
        """

        if self.base_address is not None:
            raise NotImplementedError

        async with models.AsyncSession() as session:
            category_query = (
                session.query(models.Category, models.CategoryName).outerjoin(
                    models.CategoryName,
                    sqlalchemy.and_(
                        models.CategoryName.category_id == models.Category.id,
                        models.CategoryName.source == source
                    )
                ).filter(
                    sqlalchemy.or_(
                        models.CategoryName.id.is_(None),
                        models.CategoryName.name.isnot(None)
                    )
                )
            )

            if query_categories is not None:
                category_query = category_query.filter(models.Category.name.in_(query_categories))

            services = [
                {
                    'id': category.id,
                    'name': category.name if category_name is None else category_name.name
                }
                for category, category_name in category_query.all()
            ]
            return services

    async def get_facilities(self, service_id, city_id):
        if self.base_address is not None:
            raise NotImplementedError

        async with models.AsyncSession() as session:
            facility_query = session.query(models.Facility).join(
                models.Facility.categories
            ).filter(
                models.Facility.city_id == city_id,
                models.Category.id == service_id
            )

            return [
                {
                    'id': facility.id,
                    'name': facility.name
                }
                for facility in facility_query.all()
            ]

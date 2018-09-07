import argparse
import asyncio
import datetime
import json

import sqlalchemy
import sqlalchemy.exc
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

import models
import yelp
import default
import reviews.opencare
import reviews.google
from proxies import AsyncProxyFinder

SOURCES = {
    'yelp': yelp,
}

REVIEW_SOURCES = {
    'opencare': reviews.opencare,
    'google': reviews.google
}

SEMAPHORE_DB = asyncio.Semaphore(value=1)
SEMAPHORE_SCRAPE = asyncio.Semaphore(value=100)
SEMAPHORE_REVIEW = asyncio.Semaphore(value=5)

session_engine = create_engine('sqlite:///tophealth.db')
session_maker = sessionmaker(bind=session_engine)
session = session_maker()


async def get_source_category(source, category):
    async with SEMAPHORE_DB:
        try:
            return session.query(models.CategoryName).filter(
                models.CategoryName.source == source,
                models.CategoryName.category == category
            ).one().name
        except sqlalchemy.orm.exc.NoResultFound:
            return category.name


async def get_location(city, region=None, country=None):
    async with SEMAPHORE_DB:
        query = session.query(models.Country, models.Region, models.City).select_from(
            sqlalchemy.join(
                models.Country,
                sqlalchemy.join(
                    models.Region,
                    models.City,
                    models.City.region_id == models.Region.id
                ),
                models.Region.country_id == models.Country.id
            )
        )
        if city is not None and 'name' in city:
            query = query.filter(models.City.name == city['name'])

        if region is not None:
            if 'name' in region:
                query = query.filter(models.Region.name == region['name'])
            if 'code' in region:
                query = query.filter(models.Region.code == region['code'])

        if country is not None:
            if 'name' in country:
                query = query.filter(models.Country.name == country['name'])
            if 'code' in country:
                query = query.filter(models.Country.code == country['code'])

        results = []
        for country, region, city in query.all():
            results.append({
                'country': {
                    'name': country.name,
                    'code': country.code
                },
                'region': {
                    'name': region.name,
                    'code': region.code
                },
                'city': {
                    'name': city.name
                }
            })

        return results


async def get_locations_categories():
    async with SEMAPHORE_DB:
        query = session.query(
            models.Category, models.City, models.Region, models.Country
        ).join(
            (models.Category, models.Facility.categories),
        ).join(
            models.City, models.City.id == models.Facility.city_id
        ).join(
            models.Region, models.Region.id == models.City.region_id
        ).join(
            models.Country, models.Country.id == models.Region.country_id
        )

        for category, city, region, country in query.all():
            yield (
                category.name,
                {
                    'city': {
                        'name': city.name
                    },
                    'region': {
                        'name': region.name,
                        'code': region.code
                    },
                    'country': {
                        'name': country.name,
                        'code': country.code
                    }
                }
            )


async def populate(business):
    async with SEMAPHORE_DB:
        source_categories = (
            session.query(models.CategoryName).filter(
                models.CategoryName.source == business['source'],
                models.CategoryName.name.in_(business['categories'])
            )
        ).all()

        try:
            filter_expressions = []
            if 'name' in business['location']['region']:
                filter_expressions.append(
                    func.lower(models.Region.name) == func.lower(business['location']['region']['name'])
                )
            if 'code' in business['location']['region']:
                filter_expressions.append(
                    models.Region.code == business['location']['region']['code']
                )

            region_id, = (
                session.query(models.Region.id)
                .filter(sqlalchemy.or_(*filter_expressions))
            ).one()

        except sqlalchemy.orm.exc.NoResultFound:
            print(f"Unknown region {business['location']['region']}")
            return False

        try:
            city_id, = (
                session.query(models.City.id).filter(
                    func.lower(models.City.name) == func.lower(business['location']['city']),
                    models.City.region_id == region_id,
                )
            ).one()

        except sqlalchemy.orm.exc.NoResultFound:
            print(f"Unknown city {business['location']['city']}, {business['location']['region']}")
            return False

        facility = session.query(models.Facility).filter(
            func.lower(models.Facility.name) == func.lower(business['name']),
            models.Facility.city_id == city_id
        ).first()

        if facility is None:
            facility = models.Facility(
                name=business['name'],
                city_id=city_id
            )
            session.add(facility)

        for source_category in source_categories:
            facility.categories.append(source_category.category)

        facility_info = models.FacilityInfo(
            facility=facility,
            fetch_date=datetime.datetime.now(datetime.timezone.utc),
            source=business['source'],

            image_url=business['logo'],
            phone=business['phone'],
            website_url=business['website'],
            address=business['address'],

            about=business['about'],
        )
        session.add(facility_info)
        try:
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            session.rollback()

        session.add(models.Review(
            facility=facility,
            source=business['source'],
            rating=business['rating']['stars'],
            count=business['rating']['count'],
        ))
        try:
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            session.rollback()

        try:
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            session.rollback()
            return False

    return True


async def populate_reviews(review_data):
    async with SEMAPHORE_DB:
        try:
            existed_review = session.query(models.Review).filter(
                models.Review.facility_id == review_data['facility_id'],
                models.Review.source == review_data['source']
            ).one()
            existed_review.rating = review_data['stars']
            existed_review.count = review_data['count']
            try:
                session.commit()
            except sqlalchemy.exc.IntegrityError:
                session.rollback()

        except sqlalchemy.orm.exc.NoResultFound:
            session.add(models.Review(
                facility_id=review_data['facility_id'],
                source=review_data['source'],
                rating=review_data['stars'],
                count=review_data['count'],
            ))
            try:
                session.commit()
            except sqlalchemy.exc.IntegrityError:
                session.rollback()


async def scrape(proxy_manager, source, category, city):
    async with SEMAPHORE_SCRAPE:
        scraper = SOURCES[source]

        async def append_facility(business):
            business.update({
                'source': source
            })
            await populate(business)

        await scraper.scrape(
            callback=append_facility,
            proxy_manager=proxy_manager,

            category={
                'name': category.name,
            },
            country={
                'name': city.region.country.name,
                'code': city.region.country.code
            },
            region={
                'name': city.region.name,
                'code': city.region.code
            },
            city={
                'name': city.name
            }
        )


async def scrape_reviews(source, category, city, facilities):
    async with SEMAPHORE_REVIEW:
        source_category = await get_source_category(source, category)
        if source_category is None:
            return

        scraper = REVIEW_SOURCES[source]

        async def append_review(review):
            for facility in facilities:
                if facility.name == review['facility_name']:
                    review.update({
                        'facility_id': facility.id
                    })
                    break

            review.update({
                'source': source,
            })
            await populate_reviews(review)

        await scraper.scrape_reviews(
            callback=append_review,

            category={
                'name': source_category
            },
            country={
                'name': city.region.country.name,
                'code': city.region.country.code
            },
            region={
                'name': city.region.name,
                'code': city.region.code
            },
            city={
                'name': city.name
            },
            clinic_names={facility.name for facility in facilities}
        )


def generate_result(city_name=None, region_name=None, country_name=None, categories=None):
    last_fetch = (
        session.query(
            models.FacilityInfo.facility_id.label('facility_id'),
            sqlalchemy.func.max(models.FacilityInfo.fetch_date).label('fetch_date')
        )
        .group_by(
            models.FacilityInfo.facility_id,
            models.FacilityInfo.source
        )
        .subquery('last_fetch')
    )

    query = (
        session.query(models.Facility, models.FacilityInfo).select_from(
            sqlalchemy.join(
                models.Country,
                sqlalchemy.join(
                    models.Region,
                    sqlalchemy.join(
                        models.City,
                        sqlalchemy.join(
                            models.Facility,
                            sqlalchemy.join(
                                models.FacilityInfo, last_fetch,
                                models.FacilityInfo.facility_id == last_fetch.c.facility_id
                            ),
                            models.Facility.id == models.FacilityInfo.facility_id
                        ),
                        models.Facility.city_id == models.City.id
                    ),
                    models.City.region_id == models.Region.id
                ),
                models.Region.country_id == models.Country.id
            ),
        )
        .filter(models.FacilityInfo.fetch_date == last_fetch.c.fetch_date)
        .filter(models.FacilityInfo.source.in_(list(SOURCES)))
        .order_by(sqlalchemy.asc(models.Facility.id))
    )

    if city_name is not None:
        query = query.filter(
            models.City.name == city_name
        )

    if region_name is not None:
        query = query.filter(
            sqlalchemy.or_(
                models.Region.name == region_name,
                models.Region.code == region_name
            )
        )

    if country_name is not None:
        query = query.filter(
            sqlalchemy.or_(
                models.Country.name == country_name,
                models.Country.code == country_name
            )
        )

    if categories is not None and len(categories) > 0:
        # noinspection PyUnresolvedReferences
        query = query.filter(
            models.Facility.categories.any(models.Category.name.in_(categories))
        )

    facilities = {}
    for facility, facility_info in query.all():
        result = facilities.get(facility.id)
        if result is None:
            result = {
                'name': facility.name,
                'location': {
                    'country': facility.city.region.country.name,
                    'region': facility.city.region.name,
                    'city': facility.city.name,
                },
                'categories': [
                    category.name for category in facility.categories
                ],
                'info': [],
                'total_reviews': 0,
                'total_rating': 0,
                'sources': [],
            }

            for review in facility.reviews:
                result['total_rating'] += float(review.rating) * review.count
                result['total_reviews'] += review.count
                result['sources'].append({
                    'name': review.source,
                    'rating': float(review.rating),
                    'reviews': review.count
                })

            if result['total_reviews'] > 0:
                result['total_rating'] /= result['total_reviews']

            facilities[facility.id] = result

        result['info'].append({
            'source': facility_info.source,
            'about': facility_info.about,
            'phone': facility_info.phone,
            'address': facility_info.address,
            'image_url': facility_info.image_url,
            'website_url': facility_info.website_url
        })

    return list(sorted(facilities.values(), key=lambda x: (-x['total_rating'], -x['total_reviews'])))


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='mode')
    subparsers.add_parser('init')

    scrape_parser = subparsers.add_parser('scrape')
    scrape_parser.add_argument('--source', choices=list(SOURCES))
    scrape_parser.add_argument('--city', help="City for scraping")
    scrape_parser.add_argument('--region', help="Region for scraping")
    scrape_parser.add_argument('--country', help="Country for scraping")
    scrape_parser.add_argument('--categories', nargs='*', help="List of categories")

    review_parser = subparsers.add_parser('reviews')
    review_parser.add_argument('--source', choices=list(REVIEW_SOURCES))
    review_parser.add_argument('--city', help="City for scraping")
    review_parser.add_argument('--region', help="Region for scraping")
    review_parser.add_argument('--country', help="Country for scraping")
    review_parser.add_argument('--categories', nargs='*', help="List of categories")

    result_parser = subparsers.add_parser('result')
    result_parser.add_argument('--city', help="City for results")
    result_parser.add_argument('--region', help="Region for results")
    result_parser.add_argument('--country', help="Country for results")
    result_parser.add_argument('--categories', nargs='*', help="List of categories")

    args = parser.parse_args()

    if args.mode == 'init':
        default.create_data(session)

    if args.mode == 'scrape' or args.mode == 'reviews':
        cities_query = session.query(models.City).select_from(
            sqlalchemy.join(
                models.Country,
                sqlalchemy.join(
                    models.Region,
                    models.City,
                    models.City.region_id == models.Region.id
                ),
                models.Region.country_id == models.Country.id
            )
        )

        city_name = args.city
        if city_name is not None:
            cities_query = cities_query.filter(
                models.City.name == city_name
            )

        region_name = args.region
        if region_name is not None:
            cities_query = cities_query.filter(
                sqlalchemy.or_(
                    models.Region.name == region_name,
                    models.Region.code == region_name
                )
            )

        country_name = args.country
        if country_name is not None:
            cities_query = cities_query.filter(
                sqlalchemy.or_(
                    models.Country.name == country_name,
                    models.Country.code == country_name
                )
            )

        categories_query = session.query(models.Category)
        if args.categories is not None and len(args.categories) > 0:
            categories_query = categories_query.filter(
                models.Category.name.in_(args.categories)
            )

        cities = cities_query.all()
        categories = categories_query.all()

        if args.mode == 'scrape':
            proxy_finder = AsyncProxyFinder()
            asyncio.ensure_future(proxy_finder.update_proxies())

            scrapers = []
            for city in cities:
                for category in categories:

                    if args.source is not None:
                        sources = [args.source]
                    else:
                        sources = list(SOURCES.keys())

                    for source in sources:
                        scrapers.append(scrape(
                            proxy_manager=proxy_finder,
                            source=source,
                            category=category,
                            city=city
                        ))

            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.gather(*scrapers))

        else:
            scrapers = []
            for city in cities:
                for category in categories:
                    facilities = category.facilities.filter(models.Facility.city == city).all()

                    if args.source is not None:
                        sources = [args.source]
                    else:
                        sources = list(REVIEW_SOURCES.keys())

                    for source in sources:
                        scrapers.append(scrape_reviews(
                            source=source,
                            category=category,
                            city=city,
                            facilities=facilities
                        ))

            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.gather(*scrapers))

    if args.mode == 'result':
        print(json.dumps(indent=4, obj={
            'facilities': generate_result(args.city, args.region, args.country, args.categories)
        }))


if __name__ == '__main__':
    main()

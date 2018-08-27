import argparse
import asyncio
import datetime
import json

import sqlalchemy
import sqlalchemy.exc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
import opencare
import yelp
import default

SOURCES = {
    'opencare': opencare,
    'yelp': yelp
}

SEMAPHORE_DB = asyncio.Semaphore(value=1)

session_engine = create_engine('sqlite:///tophealth.db')
session_maker = sessionmaker(bind=session_engine)
session = session_maker()


async def populate(business):
    async with SEMAPHORE_DB:
        try:
            category = (
                session.query(models.Category).filter(
                    models.Category.name == business['category'],
                )
            ).one()

        except sqlalchemy.orm.exc.NoResultFound:
            print(f"Unknown category {business['category']}")
            return False

        try:
            region_id, = (
                session.query(models.Region.id)
                .filter(
                    models.Region.name == business['region']
                )
            ).one()

        except sqlalchemy.orm.exc.NoResultFound:
            print(f"Unknown region {business['region']}")
            return False

        try:
            city_id, = (
                session.query(models.City.id).filter(
                    models.City.name == business['city'],
                    models.City.region_id == region_id,
                )
            ).one()

        except sqlalchemy.orm.exc.NoResultFound:
            print(f"Unknown city {business['city']}, {business['region']}")
            return False

        facility = session.query(models.Facility).filter(
            models.Facility.name == business['name'],
            models.Facility.city_id == city_id
        ).first()

        if facility is None:
            facility = models.Facility(
                name=business['name'],
                city_id=city_id
            )
            session.add(facility)

        facility.categories.append(category)

        facility_info = models.FacilityInfo(
            facility=facility,
            fetch_date=datetime.datetime.now(datetime.timezone.utc),
            source=business['source'],
            about=business['about'],
            address=business['street'],
            image_url=business['logo'],
            phone=business['phone'],
            rating_stars=business['rating']['stars'],
            reviews_count=business['rating']['reviews'],
            website_url=business['website']
        )
        session.add(facility_info)

        try:
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            return False

    return True


async def scrape(source, category, city):
    scraper = SOURCES[source]

    category = {
        'name': category.name,
        'opencare_name': category.opencare_name
    }
    region = {
        'name': city.region.name,
        'code': city.region.code
    }
    city = {
        'name': city.name
    }

    async def append_facility(business):
        business.update({
            'source': source
        })
        await populate(business)

    await scraper.scrape(append_facility, region, city, category)


def generate_result():
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
                models.Facility,
                sqlalchemy.join(
                    models.FacilityInfo, last_fetch,
                    models.FacilityInfo.facility_id == last_fetch.c.facility_id
                ),
                models.Facility.id == models.FacilityInfo.facility_id
            )
        )
        .filter(models.FacilityInfo.fetch_date == last_fetch.c.fetch_date)
        .filter(models.FacilityInfo.source.in_(list(SOURCES)))
        .order_by(sqlalchemy.asc(models.Facility.id))
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
                'info': []
            }
            facilities[facility.id] = result

        rating_stars = facility_info.rating_stars
        if rating_stars is not None:
            rating_stars = float(rating_stars)

        result['info'].append({
            'source': facility_info.source,
            'about': facility_info.about,
            'phone': facility_info.phone,
            'address': facility_info.address,
            'image_url': facility_info.image_url,
            'rating_stars': rating_stars,
            'reviews': facility_info.reviews_count,
            'website_url': facility_info.website_url
        })

    for facility in facilities.values():
        total_reviews = 0
        total_rating = 0.0
        source_count = 0
        for info in facility['info']:
            # noinspection PyTypeChecker
            rating_part = info['rating_stars']

            if rating_part is not None:
                total_rating += float(rating_part)
                source_count += 1

            # noinspection PyTypeChecker
            total_reviews += info['reviews']

        facility['total_reviews'] = total_reviews
        facility['total_rating'] = 0
        if source_count > 0:
            facility['total_rating'] = total_rating / source_count

    return list(sorted(facilities.values(), key=lambda x: -x['total_rating']))


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='mode')
    init_parser = subparsers.add_parser('init')
    scrape_parser = subparsers.add_parser('scrape')
    result_parser = subparsers.add_parser('result')

    args = parser.parse_args()

    if args.mode == 'init':
        default.create_data(session)

    if args.mode == 'scrape':
        loop = asyncio.get_event_loop()
        cities = session.query(models.City).all()
        categories = session.query(models.Category).all()

        for city in cities:
            for category in categories:
                for source in SOURCES:
                    loop.run_until_complete(scrape(
                        source=source,
                        category=category,
                        city=city
                    ))

    if args.mode == 'result':
        print(json.dumps(indent=4, obj={
            'facilities': generate_result()
        }))


if __name__ == '__main__':
    main()

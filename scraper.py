import asyncio
from contextlib import suppress
from decimal import Decimal

import sqlalchemy
import sqlalchemy.exc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
import opencare
import yelp


STOP_FLAG = False

SCRAPERS = {
    'opencare': opencare,
    'yelp': yelp
}

SEMAPHORE_DB = asyncio.Semaphore(value=1)

session_engine = create_engine('postgresql://admin:password@localhost:5432/tophealth')
session_maker = sessionmaker(bind=session_engine)
session = session_maker()


async def populate(business):
    async with SEMAPHORE_DB:
        try:
            category_id, = (
                session.query(models.Category.id).filter(
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

        facility = models.Facility(
            name=business['name'],
            about=business['about'],
            category_id=category_id,
            city_id=city_id,
            street=business['street'],
            logo_url=business['logo'],
            phone=business['phone'],
            rating_stars=business['rating']['stars'],
            website_url=business['website']
        )
        session.add(facility)

        try:
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            session.rollback()
            print(f"Existing facility {business['name']} in {business['city']}, {business['region']}")
            return False

    return True


async def scrape(site, category, region, city):
    global STOP_FLAG
    scraper = SCRAPERS[site]
    await scraper.scrape(populate, region, city, category)


async def create_default_data():
    async with SEMAPHORE_DB:
        category = models.Category(
            name='chiropractors'
        )
        session.add(category)
        try:
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            session.rollback()

        ontario = models.Region(
            name='ontario'
        )
        session.add(ontario)
        try:
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            session.rollback()
            ontario = session.query(models.Region).filter(
                models.Region.name == 'ontario'
            ).one()

        toronto = models.City(
            name='toronto',
            region=ontario
        )
        session.add(toronto)
        try:
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            session.rollback()
            toronto = session.query(models.City).filter(
                models.City.name == 'toronto',
                models.City.region_id == ontario.id
            ).one()


def main():
    asyncio.get_event_loop().run_until_complete(create_default_data())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(scrape(
        site='opencare',
        category='chiropractors',
        region='ontario',
        city='toronto'
    ))


if __name__ == '__main__':
    main()

import asyncio
import os

import aiohttp_jinja2
import jinja2
import sqlalchemy
from aiohttp import web

import models

routes = web.RouteTableDef()


async def get_location(city, region=None, country=None):
    async with models.AsyncSession() as session:
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
    async with models.AsyncSession() as session:
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
        ).group_by(
            models.Category.id,
            models.City.id,
            models.Region.id,
            models.Country.id
        ).having(
            sqlalchemy.func.count(models.Facility.id) > 0
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


async def generate_result(city_name=None, region_name=None, country_name=None, categories=None):
    async with models.AsyncSession() as session:
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


@routes.get('/')
@aiohttp_jinja2.template('tops.html')
async def index(request):
    categories = []
    async for result in get_locations_categories():
        categories.append(result)

    return {
        'categories': categories
    }


@routes.get('/{region}/{city}/{category}')
@aiohttp_jinja2.template('tophealth.html')
async def get_top(request):
    category = request.match_info['category']
    region_code = request.match_info['region']
    city_name = request.match_info['city']

    location, = await get_location(
        city={'name': city_name},
        region={'code': region_code},
    )

    facilities = await generate_result(
        city_name=city_name,
        region_name=region_code,
        categories=[category]
    )
    return {
        "category": category,
        "location": location,
        "facilities": facilities
    }


async def create_app():
    app = web.Application()
    app.add_routes(routes)
    aiohttp_jinja2.setup(
        app=app,
        loader=jinja2.FileSystemLoader(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')
        )
    )
    return app


def start_app():
    app = asyncio.get_event_loop().run_until_complete(create_app())
    web.run_app(app)


if __name__ == '__main__':
    start_app()

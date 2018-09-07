import asyncio
import os

import aiohttp
import aiohttp_jinja2
import jinja2
from aiohttp import web

import models
from tophealth import generate_result
import tophealth

routes = web.RouteTableDef()


@routes.get('/')
@aiohttp_jinja2.template('tops.html')
async def index(request):
    categories = []
    async for result in tophealth.get_locations_categories():
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

    location, = await tophealth.get_location(
        city={'name': city_name},
        region={'code': region_code},
    )

    facilities = generate_result(
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

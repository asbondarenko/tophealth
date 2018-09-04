import asyncio
import os

import aiohttp
import aiohttp_jinja2
import jinja2
from aiohttp import web

from tophealth import generate_result

routes = web.RouteTableDef()


@routes.get('/')
@aiohttp_jinja2.template('tophealth.html')
async def index(request):
    categories = [
        # "Chiropractors",
        "Acupuncture",
    ]
    facilities = generate_result(
        city_name='Toronto',
        region_name='Ontario',
        categories=categories
    )

    return {
        "category": categories[0],
        "location": {
            "country": "Canada",
            "region": "Ontario",
            "city": "Toronto"
        },
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

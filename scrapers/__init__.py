from .yelp import ScrapeYelp
from .google import ReviewGoogle
from .opencare import ReviewOpencare


SCRAPER_SOURCES = {
    'yelp': ScrapeYelp
}

REVIEWS_SOURCES = {
    'google': ReviewGoogle,
    'opencare': ReviewOpencare
}

__all__ = (SCRAPER_SOURCES, REVIEWS_SOURCES)

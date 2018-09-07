import csv
import os

import sqlalchemy.exc
import models


def create_data(session):
    with open('default/categories.csv') as f:
        for category in csv.DictReader(f, fieldnames=['name']):
            session.add(models.Category(
                name=category['name']
            ))
            try:
                session.commit()
            except sqlalchemy.exc.IntegrityError:
                session.rollback()

    for source in os.listdir('default/sources/'):
        source_path = os.path.join('default/sources/', source)
        if not os.path.isdir(source_path):
            continue

        categories_path = os.path.join(source_path, 'categories.csv')
        if not os.path.exists(categories_path):
            continue

        with open(categories_path) as f:
            for source_category in csv.DictReader(f, fieldnames=['name', 'alias']):
                if len(source_category['alias']) == 0:
                    continue

                category = session.query(models.Category).filter(models.Category.name == source_category['name']).one()
                session.add(models.CategoryName(
                    source=source,
                    name=source_category['alias'],
                    category=category
                ))

                try:
                    session.commit()
                except sqlalchemy.exc.IntegrityError:
                    session.rollback()

    with open('default/countries.csv') as f:
        for country in csv.DictReader(f, fieldnames=['name', 'code']):
            session.add(models.Country(
                name=country['name'],
                code=country['code'],
            ))
            try:
                session.commit()
            except sqlalchemy.exc.IntegrityError:
                session.rollback()

    with open('default/regions.csv') as f:
        for region in csv.DictReader(f, fieldnames=['country', 'name', 'code']):
            country = session.query(models.Country).filter(models.Country.name == region['country']).one()
            session.add(models.Region(
                name=region['name'],
                code=region['code'],
                country=country
            ))
            try:
                session.commit()
            except sqlalchemy.exc.IntegrityError:
                session.rollback()

    with open('default/cities.csv') as f:
        for city in csv.DictReader(f, fieldnames=['country_code', 'region_code', 'name']):
            region = session.query(models.Region).select_from(
                sqlalchemy.join(
                    models.Country,
                    models.Region,
                    models.Country.id == models.Region.country_id
                )
            ).filter(
                models.Region.code == city['region_code'],
                models.Country.code == city['country_code'],
            ).one()

            session.add(models.City(
                name=city['name'],
                region=region
            ))
            try:
                session.commit()
            except sqlalchemy.exc.IntegrityError:
                session.rollback()

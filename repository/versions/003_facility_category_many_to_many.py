from sqlalchemy import *
from migrate import *

meta = MetaData()


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata

    meta.bind = migrate_engine

    facility = Table('facility', meta, autoload=True)
    Table('category', meta, autoload=True)

    facility_category = Table(
        'facility_category', meta,
        Column('facility_id', Integer, ForeignKey('facility.id'), primary_key=True),
        Column('category_id', Integer, ForeignKey('category.id'), primary_key=True)
    )
    facility_category.create()

    for facility_id, category_id in migrate_engine.execute(select([facility.c.id, facility.c.category_id])):
        if category_id is None:
            continue

        migrate_engine.execute(
            facility_category.insert().values(
                facility_id=facility_id,
                category_id=category_id
            )
        )

    facility.c.category_id.drop()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    meta.bind = migrate_engine

    facility = Table('facility', meta, autoload=True)
    Table('category', meta, autoload=True)

    category_id = Column('category_id', Integer, ForeignKey("category.id"), nullable=True)
    category_id.create(facility)

    facility_category = Table('facility_category', meta, autoload=True)

    for facility_id, category_id in migrate_engine.execute(select([facility_category.c.facility_id, facility_category.c.category_id])):
        migrate_engine.execute(
            facility.update().where(facility.c.id == facility_id).values(
                category_id=category_id
            )
        )

    facility_category.drop()

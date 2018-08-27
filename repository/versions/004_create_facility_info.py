import datetime

from sqlalchemy import *
from migrate import *

meta = MetaData()

facility_info = Table(
    'facility_info', meta,

    Column('id', Integer, Sequence('facility_info_id_seq', metadata=meta), primary_key=True),

    Column('facility_id', Integer, ForeignKey('facility.id'), nullable=False),
    Column('fetch_date', DateTime, nullable=False),

    Column('source', String(32)),

    Column('about', Text),
    Column('phone', String(32)),
    Column('address', Text, nullable=False),

    Column('image_url', Text),
    Column('rating_stars', Float(asdecimal=True)),
    Column('website_url', Text)
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata

    meta.bind = migrate_engine
    facility = Table('facility', meta, autoload=True)

    facility_info.create()

    for facility_obj in migrate_engine.execute(select([facility])):
        migrate_engine.execute(
            facility_info.insert().values(
                about=facility_obj.about,
                phone=facility_obj.phone,
                address=facility_obj.address,
                image_url=facility_obj.logo_url,
                rating_stars=facility_obj.rating_stars,
                website_url=facility_obj.website_url,

                facility_id=facility_obj.id,
                fetch_date=datetime.datetime.now(tz=datetime.timezone.utc)
            )
        )

    facility.c.about.drop()
    facility.c.phone.drop()
    facility.c.address.drop()
    facility.c.logo_url.drop()
    facility.c.rating_stars.drop()
    facility.c.website_url.drop()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.

    meta.bind = migrate_engine
    facility = Table('facility', meta, autoload=True)

    Column('about', Text).create(facility)
    Column('address', Text).create(facility)
    Column('logo_url', Text).create(facility)
    Column('phone', String(32)).create(facility)
    Column('rating_stars', Float(asdecimal=True)).create(facility)
    Column('website_url', Text).create(facility)
    # Column('website_url', Text)

    last_fetch = (
        select([facility_info.c.facility_id, func.max(facility_info.c.fetch_date).label("fetch_date")])
        .group_by(facility_info.c.facility_id)
        .alias("last_fetch")
    )
    query = (
        select([facility_info]).select_from(
            join(
                facility_info, last_fetch,
                facility_info.c.facility_id == last_fetch.c.facility_id
            ),
        )
        .where(facility_info.c.fetch_date == last_fetch.c.fetch_date)
    )

    for facility_info_obj in migrate_engine.execute(query):
        migrate_engine.execute(
            facility.update()
            .where(facility.c.id == facility_info_obj.facility_id)
            .values(
                about=facility_info_obj.about,
                phone=facility_info_obj.phone,
                address=facility_info_obj.address,
                logo_url=facility_info_obj.image_url,
                rating_stars=facility_info_obj.rating_stars,
                website_url=facility_info_obj.website_url,
            )
        )

    facility.c.address.alter(nullable=False)

    facility_info.drop()

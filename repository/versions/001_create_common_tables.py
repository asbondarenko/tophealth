from sqlalchemy import *
# from migrate import *

meta = MetaData()


category = Table(
    'category', meta,

    Column('id', Integer, Sequence('category_id_seq', metadata=meta), primary_key=True),
    Column('name', String(64), nullable=False),

    UniqueConstraint('name', name='category_uc')
)


country = Table(
    'country', meta,

    Column('id', Integer, Sequence('country_id_seq'), primary_key=True),
    Column('name', String(64), nullable=False),
    Column('code', String(16), nullable=False),

    UniqueConstraint('name', name='country_name_uc'),
    UniqueConstraint('code', name='country_code_uc'),
)


region = Table(
    'region', meta,

    Column('id', Integer, Sequence('region_id_seq'), primary_key=True),
    Column('name', String(64), nullable=False),
    Column('code', String(16), nullable=False),
    Column('country_id', Integer, ForeignKey('country.id'), nullable=False),

    UniqueConstraint('name', name='region_name_uc'),
    UniqueConstraint('code', name='region_code_uc'),
)

city = Table(
    'city', meta,

    Column('id', Integer, Sequence('city_id_seq'), primary_key=True),
    Column('name', String(64), nullable=False),
    Column('region_id', Integer, ForeignKey('region.id'), nullable=False),

    UniqueConstraint('name', 'region_id', name='city_uc'),
)

facility = Table(
    'facility', meta,

    Column('id', Integer, Sequence('facility_id_seq'), primary_key=True),
    Column('name', String(256), nullable=False),
    Column('about', Text),
    Column('category_id', Integer, ForeignKey("category.id")),
    Column('city_id', Integer, ForeignKey("city.id"), nullable=False),
    Column('address', Text, nullable=False),
    Column('logo_url', Text),
    Column('phone', String(32)),
    Column('rating_stars', Float(asdecimal=True)),
    Column('website_url', Text),

    UniqueConstraint('name', 'category_id', 'city_id', name='facility_uc'),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata

    meta.bind = migrate_engine
    category.create()
    country.create()
    region.create()
    city.create()
    facility.create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.

    meta.bind = migrate_engine
    facility.drop()
    city.drop()
    region.drop()
    country.drop()
    category.drop()

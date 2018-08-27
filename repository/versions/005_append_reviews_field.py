from sqlalchemy import *
from migrate import *


meta = MetaData()


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta.bind = migrate_engine

    facility_info = Table('facility_info', meta, autoload=True)
    reviews_count = Column('reviews_count', Integer, server_default='0', nullable=False)
    reviews_count.create(facility_info)


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    meta.bind = migrate_engine

    facility_info = Table('facility_info', meta, autoload=True)
    facility_info.c.reviews_count.drop()

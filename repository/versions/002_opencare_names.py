from sqlalchemy import *
from migrate import *


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = MetaData(bind=migrate_engine)

    category = Table('category', meta, autoload=True)
    opencare_name = Column('opencare_name', String(64), nullable=True)
    opencare_name.create(category)


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    meta = MetaData(bind=migrate_engine)

    account = Table('category', meta, autoload=True)
    account.c.opencare_name.drop()

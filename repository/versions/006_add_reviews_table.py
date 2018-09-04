from sqlalchemy import *
from migrate import *


meta = MetaData()


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta.bind = migrate_engine

    Table('facility', meta, autoload=True)
    review = Table(
        'review', meta,

        Column('id', Integer, Sequence('review_id_seq', metadata=meta), primary_key=True),
        Column('author', String(64), nullable=False),
        Column('content', Text, nullable=False),
        Column('rating', Float(asdecimal=True), nullable=False),
        Column('multiplier', Integer, nullable=False, server_default='1'),
        Column('facility_id', Integer, ForeignKey("facility.id")),

        UniqueConstraint('facility_id', 'content', name='review_uc')
    )
    review.create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    meta.bind = migrate_engine
    review = Table('review', meta, autoload=True)
    review.drop()


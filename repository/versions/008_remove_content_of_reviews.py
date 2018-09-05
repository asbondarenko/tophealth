from sqlalchemy import *
from migrate import *

meta = MetaData()


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta.bind = migrate_engine
    review = Table('review', meta, autoload=True)

    UniqueConstraint(table=review, name='review_uc').drop()
    review.c.content.drop()
    UniqueConstraint(review.c.facility_id, review.c.author, name='review_uc').create()
    review.c.author.alter(name='source')
    review.c.multiplier.alter(name='count')

    facility_info = Table('facility_info', meta, autoload=True)
    facility_info.c.rating_stars.drop()
    facility_info.c.reviews_count.drop()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    meta.bind = migrate_engine

    review = Table('review', meta, autoload=True)
    UniqueConstraint(table=review, name='review_uc').drop()
    Column('content', Text, nullable=True).create(review)

    for review_id, review_author in migrate_engine.execute(select([review.c.id, review.c.source])):
        migrate_engine.execute(
            review.update().where(review.c.id == review_id).values(
                content=f'__{review_author} generic review'
            )
        )
    review.c.source.alter(name='author')
    review.c.count.alter(name='multiplier')

    review.c.content.alter(nullable=False)
    UniqueConstraint(review.c.facility_id, review.c.content, name='review_uc').create()

    facility_info = Table('facility_info', meta, autoload=True)
    Column('rating_stars', Float(asdecimal=True), server_default='0').create(facility_info)
    Column('reviews_count', Integer, nullable=False, server_default='0').create(facility_info)

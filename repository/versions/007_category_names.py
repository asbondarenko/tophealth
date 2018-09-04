from sqlalchemy import *
from migrate import *


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = MetaData(bind=migrate_engine)

    category = Table('category', meta, autoload=True)
    category.c.opencare_name.drop()

    category_name = Table(
        'category_name', meta,
        Column('id', Integer, Sequence('category_name_id_seq', metadata=meta), primary_key=True),
        Column('source', String(32), nullable=False),
        Column('name', String(64), nullable=False),
        Column('category_id', Integer, ForeignKey("category.id")),

        UniqueConstraint('source', 'name', name='category_name_uc')
    )
    category_name.create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    meta = MetaData(bind=migrate_engine)

    category_name = Table('category_name', meta, autoload=True)
    category_name.drop()

    category = Table('category', meta, autoload=True)
    opencare_name = Column('opencare_name', String(64), nullable=True)
    opencare_name.create(category)

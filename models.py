import asyncio

from sqlalchemy import Column, Sequence, Integer, String, ForeignKey, Text, Float, UniqueConstraint, Table, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Model = declarative_base()


facility_category = Table(
    'facility_category', Model.metadata,
    Column('facility_id', Integer, ForeignKey('facility.id')),
    Column('category_id', Integer, ForeignKey('category.id'))
)


class Category(Model):
    __tablename__ = 'category'
    __table_args__ = (
        UniqueConstraint('name', name='category_uc'),
    )

    id = Column(Integer, Sequence('category_id_seq'), primary_key=True)
    name = Column(String(64), nullable=False)

    facilities = relationship("Facility", lazy='dynamic', secondary=facility_category, back_populates='categories')
    category_names = relationship("CategoryName", lazy='dynamic', back_populates='category')


class CategoryName(Model):
    __tablename__ = 'category_name'
    __table_args__ = (
        UniqueConstraint('source', 'name', name='category_name_uc'),
    )

    id = Column(Integer, Sequence('category_name_id_seq'), primary_key=True)
    source = Column(String(32), nullable=False)
    name = Column(String(64), nullable=False)

    category_id = Column(Integer, ForeignKey("category.id"))
    category = relationship("Category", back_populates="category_names")


class Country(Model):
    __tablename__ = 'country'
    __table_args__ = (
        UniqueConstraint('name', name='country_name_uc'),
        UniqueConstraint('code', name='country_code_uc'),
    )

    id = Column(Integer, Sequence('country_id_seq'), primary_key=True)
    name = Column(String(64), nullable=False)
    code = Column(String(16), nullable=False)

    regions = relationship("Region", back_populates='country')


class Region(Model):
    __tablename__ = 'region'
    __table_args__ = (
        UniqueConstraint('name', name='region_name_uc'),
        UniqueConstraint('code', name='region_code_uc'),
    )

    id = Column(Integer, Sequence('region_id_seq'), primary_key=True)
    name = Column(String(64), nullable=False)
    code = Column(String(16), nullable=False)

    country_id = Column(Integer, ForeignKey('country.id'), nullable=False)
    country = relationship("Country", back_populates="regions")

    cities = relationship("City", back_populates='region')


class City(Model):
    __tablename__ = 'city'
    __table_args__ = (
        UniqueConstraint('name', 'region_id', name='city_uc'),
    )

    id = Column(Integer, Sequence('city_id_seq'), primary_key=True)
    name = Column(String(64), nullable=False)
    region_id = Column(Integer, ForeignKey('region.id'), nullable=False)
    region = relationship("Region", back_populates="cities")

    facilities = relationship("Facility", back_populates='city')


class Facility(Model):
    __tablename__ = 'facility'
    __table_args__ = (
        UniqueConstraint('name', 'city_id', name='facility_uc'),
    )

    id = Column(Integer, Sequence('facility_id_seq'), primary_key=True)
    name = Column(String(256), nullable=False)

    categories = relationship("Category", secondary=facility_category, back_populates="facilities")

    city_id = Column(Integer, ForeignKey("city.id"), nullable=False)
    city = relationship("City", back_populates="facilities")

    fetches = relationship("FacilityInfo", back_populates="facility")
    reviews = relationship("Review", back_populates="facility")


class FacilityInfo(Model):
    __tablename__ = 'facility_info'

    id = Column(Integer, Sequence('facility_info_id_seq'), primary_key=True)

    about = Column(Text)
    phone = Column(String(32))
    address = Column(Text, nullable=False)

    image_url = Column(Text)
    website_url = Column(Text)

    facility_id = Column(Integer, ForeignKey('facility.id'), nullable=False)
    facility = relationship("Facility", back_populates="fetches")

    fetch_date = Column(DateTime, nullable=False)

    source = Column(String(32))


class Review(Model):
    __tablename__ = 'review'
    __table_args__ = (
        UniqueConstraint('facility_id', 'source', name='review_uc'),
    )

    id = Column(Integer, Sequence('review_id_seq'), primary_key=True)
    source = Column(String(64), nullable=False)
    rating = Column(Float(asdecimal=True), nullable=False)
    count = Column(Integer, nullable=False, default=1)
    facility_id = Column(Integer, ForeignKey("facility.id"))

    facility = relationship("Facility", back_populates="reviews")


class AsyncSession:
    __session_engine = create_engine('sqlite:///tophealth.db')
    __session_maker = sessionmaker(bind=__session_engine)
    __session = __session_maker()
    __semaphore = asyncio.Semaphore()

    async def __enter(self, *args, **kwargs):
        await self.__semaphore.__aenter__(*args, **kwargs)
        return self.__session

    def __aenter__(self):
        return self.__enter()

    async def __leave(self, *args, **kwargs):
        await self.__semaphore.__aexit__(*args, **kwargs)

    def __aexit__(self, *args, **kwargs):
        return self.__leave(*args, **kwargs)

from sqlalchemy import Column, Sequence, Integer, String, ForeignKey, Text, Float, UniqueConstraint, Table, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

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
    rating_stars = Column(Float(asdecimal=True))
    reviews_count = Column(Integer, nullable=False)
    website_url = Column(Text)

    facility_id = Column(Integer, ForeignKey('facility.id'), nullable=False)
    facility = relationship("Facility", back_populates="fetches")

    fetch_date = Column(DateTime, nullable=False)

    source = Column(String(32))


class Review(Model):
    __tablename__ = 'review'
    __table_args__ = (
        UniqueConstraint('facility_id', 'content', name='review_uc'),
    )

    id = Column(Integer, Sequence('review_id_seq'), primary_key=True)
    author = Column(String(64), nullable=False)
    content = Column(Text, nullable=False)
    rating = Column(Float(asdecimal=True), nullable=False)
    multiplier = Column(Integer, nullable=False, default=1)
    facility_id = Column(Integer, ForeignKey("facility.id"))

    facility = relationship("Facility", back_populates="reviews")

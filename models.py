from sqlalchemy import Column, Sequence, Integer, String, ForeignKey, Text, Float, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Model = declarative_base()


class Category(Model):
    __tablename__ = 'category'
    __table_args__ = (
        UniqueConstraint('name', name='category_uc'),
    )

    id = Column(Integer, Sequence('category_id_seq'), primary_key=True)
    name = Column(String(64), nullable=False)

    facilities = relationship("Facility", back_populates='category')


class Region(Model):
    __tablename__ = 'region'
    __table_args__ = (
        UniqueConstraint('name', name='region_uc'),
    )

    id = Column(Integer, Sequence('region_id_seq'), primary_key=True)
    name = Column(String(64), nullable=False)

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
        UniqueConstraint('name', 'category_id', 'city_id', name='facility_uc'),
    )

    id = Column(Integer, Sequence('facility_id_seq'), primary_key=True)
    name = Column(String(256), nullable=False)
    about = Column(Text)

    category_id = Column(Integer, ForeignKey("category.id"), nullable=False)
    category = relationship("Category", back_populates="facilities")

    city_id = Column(Integer, ForeignKey("city.id"), nullable=False)
    city = relationship("City", back_populates="facilities")

    street = Column(Text, nullable=False)
    logo_url = Column(Text)
    phone = Column(String(32))
    rating_stars = Column(Float(asdecimal=True))
    website_url = Column(Text)

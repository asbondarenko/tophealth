import sqlalchemy.exc

import models


PLACES = [
    ('Canada', 'CA', [
        ('Ontario', 'ON', [
            'Toronto',
        ]),
    ]),
    ("United States", 'US', [
        ('Florida', 'FL', [
            'Miami',
        ]),
    ])
]

CATEGORIES = [
    ('Acupuncture', 'Acupuncture', 'acupuncturists'),
    ('Allergists', 'Allergists', None),
    ('Audiologists', 'Audiologist', 'audiologists'),
    ('Cardiologists', 'Cardiologists', None),
    ('Chiropractors', 'Chiropractors', 'chiropractors'),
    ('Cosmetic Surgeons', 'Cosmetic Surgeons', None),
    ('Dentists', 'Dentists', 'dentists'),
    ('Dermatologists', 'Dermatologists', 'dermatologists'),
    ('Ear Nose and Throat (ENT) Doctors', 'Ear Nose & Throat', None),
    ('Endocrinologists', None, 'endocrinologists'),
    ('Endodontists', 'Endodontists', 'endodontists'),
    ('Family Doctors', 'Family Practice', 'family-doctors'),
    ('Gastroenterologists', 'Gastroenterologist', None),
    ('Gynecologists', 'Obstetricians & Gynecologists', None),
    ('Homeopath', None, 'homeopaths'),
    ('Massage therapy', 'Massage Therapy', None),
    ('Naturopath', 'Naturopathic/Holistic', 'naturopaths'),
    ('Nephrologists', 'Nephrologists', None),
    ('Neurologists', 'Neurologist', None),
    ('Neurosurgeons', None,  None),
    ('Occupational Therapy', 'Occupational Therapy',  'occupational-therapists'),
    ('Oncologists', 'Oncologist', None),
    ('Ophthalmologists', 'Ophthalmologists', 'ophthalmologists'),
    ('Optometrists', 'Optometrists', 'optometrists'),
    ('Oral Surgeons', 'Oral Surgeons', 'oral-surgeons'),
    ('Orthodontists', 'Orthodontists', 'orthodontists'),
    ('Orthopedics', 'Orthopedists', 'orthopedic-surgeons'),
    ('Pediatricians', 'Pediatricians', 'pediatricians'),
    ('Physical therapy', 'Physical Therapy', 'physical-therapists'),
    ('Podiatrists', 'Podiatrists', 'podiatrists'),
    ('Proctologists', None, 'psychiatrists'),
    ('Psychiatrists', 'Psychiatrists', 'psychologists'),
    ('Psychologists', 'Psychologists', None),
    ('Pulmonologists', 'Pulmonologist', None),
    ('Rheumatologists', 'Rheumatologists', None),
    ('Sleep Doctors', 'Sleep Specialists', None),
    ('Surgeons', 'Surgeons', None),
    ('Therapists', None, None),
    ('Urologist', 'Urologists', None)
]


def create_data(session):
    def create_city(region_id, name):
        city = session.query(models.City).filter(
            models.City.name == name,
            models.City.region_id == region_id
        ).first()

        if city is None:
            city = models.City(
                name=name,
                region_id=region_id
            )
            session.add(city)
            session.commit()

        return city

    def create_region(country_id, name, code):
        region = session.query(models.Region).filter(
            models.Region.name == name,
            models.Region.code == code,
            models.Region.country_id == country_id,
        ).first()

        if region is None:
            region = models.Region(
                name=name,
                code=code,
                country_id=country_id
            )
            session.add(region)
            session.commit()

        return region

    def create_country(name, code):
        country = session.query(models.Country).filter(
            models.Country.name == name,
            models.Country.code == code,
        ).first()

        if country is None:
            country = models.Country(
                name=name,
                code=code
            )
            session.add(country)
            session.commit()

        return country

    def create_category(name, yelp_name, opencare_name):
        category = session.query(models.Category).filter(
            models.Category.name == name,
        ).first()

        if category is None:
            category = models.Category(
                name=name
            )
            session.add(category)
            session.commit()

        if yelp_name is not None:
            session.add(models.CategoryName(
                source='yelp',
                name=yelp_name,
                category=category
            ))
            try:
                session.commit()
            except sqlalchemy.exc.IntegrityError:
                session.rollback()

        if opencare_name is not None:
            session.add(models.CategoryName(
                source='opencare',
                name=opencare_name,
                category=category
            ))
            try:
                session.commit()
            except sqlalchemy.exc.IntegrityError:
                session.rollback()

        return category

    def create_places(countries):
        for country_name, country_code, regions in countries:
            country = create_country(country_name, country_code)

            for region_name, region_code, cities in regions:
                region = create_region(country.id, region_name, region_code)

                for city_name in cities:
                    create_city(region.id, city_name)

    def create_categories(categories):
        for category_names in categories:
            create_category(*category_names)

    create_places(PLACES)
    create_categories(CATEGORIES)

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
    'Acupuncture',
    'Allergists',
    'Audiologists',
    'Cardiologists',
    'Chiropractors',
    'Cosmetic Surgeons',
    'Dentists',
    'Dermatologists',
    'Ear Nose and Throat (ENT) Doctors',
    'Endocrinologists',
    'Endodontists',
    'Family Doctors',
    'Gastroenterologists',
    'Gynecologists',
    'Homeopath',
    'Massage therapy',
    'Naturopath',
    'Nephrologists',
    'Neurologists',
    'Neurosurgeons',
    'Occupational Therapy',
    'Oncologists',
    'Ophthalmologists',
    'Optometrists',
    'Oral Surgeons',
    'Orthodontists',
    'Orthopedics',
    'Pediatricians',
    'Physical therapy',
    'Podiatrists',
    'Proctologists',
    'Psychiatrists',
    'Psychologists',
    'Pulmonologists',
    'Rheumatologists',
    'Sleep Doctors',
    'Surgeons',
    'Therapists',
    'Urologist'
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

    def create_category(name):
        category = session.query(models.Category).filter(
            models.Category.name == name,
        ).first()

        if category is None:
            category = models.Category(
                name=name,
            )
            session.add(category)
            session.commit()

        return category

    def create_places(countries):
        for country_name, country_code, regions in countries:
            country = create_country(country_name, country_code)

            for region_name, region_code, cities in regions:
                region = create_region(country.id, region_name, region_code)

                for city_name in cities:
                    create_city(region.id, city_name)

    def create_categories(categories):
        for category_name in categories:
            create_category(category_name)

    create_places(PLACES)
    create_categories(CATEGORIES)

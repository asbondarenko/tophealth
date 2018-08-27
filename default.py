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
    ("Acupuncture", "acupuncturists"),
    ("Allergists", None),
    ("Audiologists", "audiologists"),
    ("Cardiologists", None),
    ("Chiropractors", "chiropractors"),
    ("Cosmetic Surgeons", None),
    ("Dentists", "dentists"),
    ("Dermatologists", "dermatologists"),
    ("Ear Nose and Throat (ENT) Doctors", None),
    ("Endocrinologists", "endocrinologists"),
    ("Endodontists", "endodontists"),
    ("Family Doctors", "family-doctors"),
    ("Gastroenterologists", None),
    ("Gynecologists", None),
    ("Homeopath", "homeopaths"),
    ("Massage therapy", None),
    ("Naturopath", "naturopaths"),
    ("Nephrologists", None),
    ("Neurologists", None),
    ("Neurosurgeons", None),
    ("Occupational Therapy", "occupational-therapists"),
    ("Oncologists", None),
    ("Ophthalmologists", "ophthalmologists"),
    ("Optometrists", "optometrists"),
    ("Oral Surgeons", "oral-surgeons"),
    ("Orthodontists", "orthodontists"),
    ("Orthopedics", "orthopedic-surgeons"),
    ("Pediatricians", "pediatricians"),
    ("Physical therapy", "physical-therapists"),
    ("Podiatrists", "podiatrists"),
    ("Proctologists", None),
    ("Psychiatrists", "psychiatrists"),
    ("Psychologists", "psychologists"),
    ("Pulmonologists", None),
    ("Rheumatologists", None),
    ("Sleep Doctors", None),
    ("Surgeons", "plastic-surgeons"),
    ("Therapists", None),
    ("Urologist", None),
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

    def create_category(name, opencare_name):
        category = session.query(models.Category).filter(
            models.Category.name == name,
        ).first()

        if category is None:
            category = models.Category(
                name=name,
                opencare_name=opencare_name
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
        for category_name, opencare_name in categories:
            create_category(category_name, opencare_name)

    create_places(PLACES)
    create_categories(CATEGORIES)

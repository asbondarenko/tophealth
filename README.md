### Install Python 3.6 and virtualenv
```console
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.6
sudo apt-get install python3-pip
```
```console
sudo pip3 install virtualenv
cd {{ project dir }}
virtualenv venv
```

### Install requirements
```console
source venv/bin/activate
pip install -r requirements.txt
```

### Prepare database
```console
python manage.py version_control
python manage.py upgrade
python tophealth.py init
```

### Start scrapers
```console
python tophealth.py scrape
```
usage
```console
usage: tophealth.py scrape [-h] [--source {yelp}] [--city CITY]
                           [--region REGION] [--country COUNTRY]
                           [--categories [CATEGORIES [CATEGORIES ...]]]

optional arguments:
  -h, --help            show this help message and exit
  --source {yelp}
  --city CITY           City for scraping
  --region REGION       Region for scraping
  --country COUNTRY     Country for scraping
  --categories [CATEGORIES [CATEGORIES ...]]
                        List of categories
```

### Start reviews scrapers
```console
python tophealth.py reviews
```
usage
```console
usage: tophealth.py reviews [-h] [--source {opencare,google}] [--city CITY]
                            [--region REGION] [--country COUNTRY]
                            [--categories [CATEGORIES [CATEGORIES ...]]]

optional arguments:
  -h, --help            show this help message and exit
  --source {opencare,google}
  --city CITY           City for scraping
  --region REGION       Region for scraping
  --country COUNTRY     Country for scraping
  --categories [CATEGORIES [CATEGORIES ...]]
                        List of categories
```

### Get result of scraping...
```console
python tophealth.py result
```
usage
```console
usage: tophealth.py result [-h] [--city CITY] [--region REGION]
                           [--country COUNTRY]
                           [--categories [CATEGORIES [CATEGORIES ...]]]

optional arguments:
  -h, --help            show this help message and exit
  --city CITY           City for results
  --region REGION       Region for results
  --country COUNTRY     Country for results
  --categories [CATEGORIES [CATEGORIES ...]]
                        List of categories
```

### ...or start server to view results in browser
```console
python app.py
```
and open url:
[http://localhost:8080/](http://localhost:8080/)
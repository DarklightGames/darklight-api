# darklight-api
RESTful API for Darkest Hour: Europe '44-'45 telemetry data.

## Prerequisites
* Python 3.5.2

## Installation
    cd C:\darklight-api
    virtualenv env
    env\Scripts\activate
    (env)> cd api
    (env)> pip install -r requirements.txt
    (env)> python manage.py migrate

## Running the server
    (env)> python manage.py runserver
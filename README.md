# darklight-api
RESTful API for Darkest Hour: Europe '44-'45 telemetry data.

## Prerequisites
* Python 3.5.2

## Installation
    cd C:\darklight-api
    virtualenv --python=python3.5 env
    env\Scripts\activate
    (env)> pip install "setuptools<58.0.0"
    (env)> pip install -r requirements.txt
    (env)> python manage.py makemigrations
    (env)> python manage.py migrate

## Running the server
    (env)> python manage.py runserver

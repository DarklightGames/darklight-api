# darklight-api
RESTful API for Darkest Hour: Europe '44-'45 telemetry data.

## Prerequisites
* Python 3.8.10

## Installation

### Windows

    cd C:\darklight-api
    virtualenv env
    env\Scripts\activate
    (env)> pip install -r requirements.txt
    (env)> python manage.py migrate

### Ubuntu

    # replace <3.8> with your major Python version
    user@ubuntu:~/darklight-api$ sudo apt install python3.8-dev
                                                  python3.8-venv
                                                  build-essential
    user@ubuntu:~/darklight-api$ python3 -m venv venv
    user@ubuntu:~/darklight-api$ source ./venv/bin/activate
    (venv) user@ubuntu:~/darklight-api$ pip install -r requirements.txt
    (venv) user@ubuntu:~/darklight-api$ python manage.py migrate

## Running the server
    (env)> python manage.py runserver

## Configuring the database

### SQlite

ez

### MySQL

 1. `sudo apt-get install mysql-server libmysqlclient-dev`
 2. `pip install mysqlclient`
 3. in [settings.py](settings.py) set:
 ```
 DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', 
        'NAME': 'darklight',
        'USER': 'root',
        'PASSWORD': 'qwerty',
        'HOST': '127.0.0.1',   # Or an IP Address that your DB is hosted on
        'PORT': '3306',
    }
}```
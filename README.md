# About
Conferency is an academic conference management system. This repo contains the backend APIs built with Python and Flask.

## Setup

Note: See Docker instruction at the end of this document

Tested with Python version 3.6.x.

Setup virtual environment and install packages:
```
virtualenv venv -p python3.6
source venv/bin/activate
pip install -r requirements/dev.txt
```

Deploy the database, generate the fake data, and start the development server
```
python manage.py deploy
python manage.py fakedata
python manage.py runserver
```

Now the APIs are served at 127.0.0.1:5000, you can use Postman to test the APIs as follows (you need to use one of the fake users to authenticate):

![Postman API Test](https://user-images.githubusercontent.com/595772/57551604-7a136e00-7337-11e9-833d-e7cf4abd20f9.png)

To use the shell during development:

    $ python manage.py shell
    >>> confs = Conference.query.all()

## Database Migration

When there are database schema changes, we can update the database: `python manage.py db migrate`, which create a new migration script, then we need to manually check the changes in the script and do `python manage.py db upgrade` to migrate to the new version.

If necessary, do `python manage.py reset_db_danger` to reset database migration - make sure to empty the database before doing that because migrate script create a table named alembic_version in the database

The following should added to the upgrade script to support MySQL for the first database initialization:

```
import os
conf_config = os.environ.get('CONF_CONFIG') or 'default'
if conf_config == 'production':  # only run this for MySQL
    op.execute('SET foreign_key_checks = 0')
```

## Email Setup

Setup the local environment variables so that emails can be sent out for local testing.

Note: email addresses and domains need to be verified in AWS SES before emails can be sent out from that domain/address.

For local Testing, `vim ~/.bash_profile` and add the following to the file:

```
export MAIL_SERVER='email-smtp.us-east-1.amazonaws.com'
export MAIL_USERNAME='Amazon Smtp Username'
export MAIL_PASSWORD='Amazon Smtp Password'
export CONF_MAIL_SENDER='Conferency <no-reply@conferency.com>'
export CONF_ADMIN='admin@conferency.com'
export CONF_SUPPORT='support@conferency.com'
```

## Docker Setup

install docker first: `brew cask install docker`

run `docker info` to see if the installation is successful.

Move to the root of the project and create a file `conferency.env`. Save the content below in it. Remember to fill correct values of variables.

```
MAIL_SERVER=
MAIL_USERNAME=
MAIL_PASSWORD=
CONF_MAIL_SENDER=Conferency <xxx@xxx.com>
CONF_ADMIN=xxx@xxx.com
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
AWS_ACCESS_KEY=
AWS_SECRET_KEY=
PAPER_BUCKET=conferency-paper
STATIC_BUCKET=conferency-static
```

run `docker-compose up`. The docker container is running now. visit 127.0.0.1:5000

stop the container `docker-compose stop`
remove the container `docker-compose rm`

## History
Conferency was founded by [Harry Wang](https://github.com/harrywang) in 2015 and [Leon Feng](https://github.com/leon0707) was the co-founder and CTO. Conferency was open sourced in 2019.

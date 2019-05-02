FROM ubuntu:16.04
LABEL maintainer "Leon Feng <leonfeng@conferency.com>"
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y \
    build-essential \
    net-tools \
    python-pip \
    python2.7 \
    python2.7-dev
ADD . /code
WORKDIR /code
RUN pip install --upgrade pip
RUN pip install -r requirements/dev.txt
RUN python manage.py deploy
RUN python manage.py fakedata
CMD python manage.py runserver --host 0.0.0.0

#!/bin/bash

python manage.py makemigrations
python manage.py migrate

exec celery -A root worker -B --loglevel=INFO --concurrency=4
#!/bin/bash

exec celery -A root worker -B --loglevel=INFO --concurrency=4
exec celery -A root worker --loglevel=info -Q long_running_tasks --concurrency=2
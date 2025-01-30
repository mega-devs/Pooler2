#!/bin/bash

exec celery -A root worker -B --loglevel=INFO --concurrency=4
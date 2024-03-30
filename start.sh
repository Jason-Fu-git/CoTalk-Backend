#!/bin/sh
python3 manage.py makemigrations user
python3 manage.py makemigrations message
python3 manage.py makemigrations chat
python3 manage.py migrate

# start a redis server
redis-server --port 6379 --bind 127.0.0.1 &

# Run with uWSGI
uwsgi --module=CoTalkBackend.wsgi:application \
    --env DJANGO_SETTINGS_MODULE=CoTalkBackend.settings \
    --master \
    --http=0.0.0.0:80 \
    --processes=5 \
    --harakiri=20 \
    --max-requests=5000 \
    --vacuum
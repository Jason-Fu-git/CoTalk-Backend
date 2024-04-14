#!/bin/sh

# Set the password securely
export DJANGO_SUPERUSER_PASSWORD='concord'

python3 manage.py makemigrations user
python3 manage.py makemigrations message
python3 manage.py makemigrations chat
python3 manage.py makemigrations ws
python3 manage.py migrate

# Check if the superuser already exists
SUPERUSER_EXISTS=$(python manage.py shell -c "from django.contrib.auth.models import User; print(User.objects.filter(is_superuser=True).exists())")

if [ "$SUPERUSER_EXISTS" = "False" ]; then
    # Create superuser if not exists
    echo "Creating superuser..."
    echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', '$DJANGO_SUPERUSER_PASSWORD')" | python manage.py shell
    echo "Superuser created successfully."
else
    echo "Superuser already exists."
fi



# start a redis server
redis-server --port 6379 --bind 127.0.0.1 &

python3 manage.py runserver 0.0.0.0:80

# Run with uWSGI
#uwsgi --module=CoTalkBackend.wsgi:application \
#    --env DJANGO_SETTINGS_MODULE=CoTalkBackend.settings \
#    --master \
#    --http=0.0.0.0:80 \
#    --processes=5 \
#    --harakiri=20 \
#    --max-requests=5000 \
#    --vacuum


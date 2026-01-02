#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 0.1
done
echo "PostgreSQL started"

python manage.py migrate --noinput

python manage.py collectstatic --noinput

exec "$@"
#!/bin/bash

# WAIT FOR POSTGRES

if [ "$DATABASE_ENGINE" == "django.db.backends.postgresql" ]; then
  echo "Waiting for Postgres..."

  while ! nc -z $DATABASE_HOST $DATABASE_PORT &>/dev/null; do
    sleep 0.1
  done

  echo "Postgres started"
fi

exec "$@"
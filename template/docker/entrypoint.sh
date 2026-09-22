#!/bin/sh
# Yalnızca web servisi RUN_MIGRATIONS=1 ile başlatılır; worker migration çalıştırmaz.
set -e
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py migrate --noinput
    python manage.py createcachetable
fi
exec "$@"

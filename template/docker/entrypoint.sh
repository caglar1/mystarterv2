#!/bin/sh
# Yalnızca web servisi RUN_MIGRATIONS=1 ile başlatılır; worker migration çalıştırmaz.
set -e
# Eski volume'larda da bulunsun: Caddy yalnızca media/public alt klasörünü bağlar (bkz. compose.yaml).
mkdir -p "${MEDIA_ROOT:-/data/media}/public" "${MEDIA_ROOT:-/data/media}/private"
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py migrate --noinput
    python manage.py createcachetable
fi
exec "$@"

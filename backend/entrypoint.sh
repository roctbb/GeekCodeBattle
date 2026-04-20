#!/bin/sh
set -eu

export FLASK_APP=${FLASK_APP:-manage:app}
PORT=${PORT:-8086}
GUNICORN_WORKERS=${GUNICORN_WORKERS:-1}
GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-120}
GUNICORN_LOG_LEVEL=${GUNICORN_LOG_LEVEL:-info}
GUNICORN_ACCESS_LOG=${GUNICORN_ACCESS_LOG:--}
GUNICORN_ERROR_LOG=${GUNICORN_ERROR_LOG:--}

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "[backend] running migrations..."
  flask db upgrade
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

echo "[backend] starting gunicorn..."
exec gunicorn \
  --worker-class eventlet \
  --workers "${GUNICORN_WORKERS}" \
  --bind "0.0.0.0:${PORT}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --log-level "${GUNICORN_LOG_LEVEL}" \
  --access-logfile "${GUNICORN_ACCESS_LOG}" \
  --error-logfile "${GUNICORN_ERROR_LOG}" \
  manage:app

#!/bin/sh
set -e

export FLASK_APP=${FLASK_APP:-manage:app}

echo "[backend] running migrations..."
flask db upgrade

echo "[backend] starting gunicorn..."
exec gunicorn \
  --worker-class eventlet \
  --workers "${GUNICORN_WORKERS:-1}" \
  --bind "0.0.0.0:${PORT:-8086}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  manage:app

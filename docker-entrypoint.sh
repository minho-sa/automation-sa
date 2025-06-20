#!/bin/bash
set -e

mkdir -p /app/logs /app/flask_session
chmod 755 /app/logs /app/flask_session

exec "$@"
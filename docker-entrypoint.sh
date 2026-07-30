#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

# Wait for PostgreSQL to be ready if DB_HOST is set
if [ -n "$DB_HOST" ]; then
  echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
  python -c "
import socket
import time
import os
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = os.environ.get('DB_HOST', 'db')
port = int(os.environ.get('DB_PORT', 5432))
while True:
    try:
        s.connect((host, port))
        break
    except socket.error:
        time.sleep(1)
"
  echo "PostgreSQL is ready!"
fi

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting server..."
exec "$@"

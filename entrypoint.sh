#!/bin/bash
set -e

# Run database migrations
alembic upgrade head

# Allow command override (used by docker-compose for hot reload)
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

# Default startup command
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

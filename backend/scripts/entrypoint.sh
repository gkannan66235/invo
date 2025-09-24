#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Running database migrations..."
# If no versions yet but DB has tables, allow stamping.
if [ ! -d "alembic/versions" ] || [ -z "$(ls -A alembic/versions)" ]; then
  echo "[entrypoint] No migration versions found. (Optional) You may want to generate a baseline revision."
fi
alembic upgrade head || { echo "[entrypoint] Migration failed"; exit 1; }

echo "[entrypoint] Starting application..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000

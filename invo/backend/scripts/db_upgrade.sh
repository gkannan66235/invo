#!/usr/bin/env bash
set -euo pipefail
if [ ! -f alembic.ini ]; then
  echo "Run from backend directory containing alembic.ini" >&2
  exit 1
fi
alembic upgrade head

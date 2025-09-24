#!/usr/bin/env bash
set -euo pipefail
REVISION=${1:-head}
if [ ! -f alembic.ini ]; then
  echo "Run from backend directory containing alembic.ini" >&2
  exit 1
fi
echo "Stamping database at revision: $REVISION"
alembic stamp "$REVISION"

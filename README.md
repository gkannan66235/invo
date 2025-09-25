# invo

Backend + frontend application with PostgreSQL, FastAPI, Next.js, Alembic migrations, and Docker Compose.

## Quick Start (Development)

```bash
# Start Postgres only
docker compose up -d database

# (Optional) create virtualenv and install deps
cd backend
pip install -r requirements.txt -r requirements-dev.txt

# Run migrations
DATABASE_URL=postgresql+asyncpg://gst_user:gst_password_2023@localhost:5432/gst_service_center \
		python run_migrations.py

# Start backend (uses entrypoint script in container normally)
uvicorn src.main:app --reload --port 8000
```

## Migrations

Alembic configuration lives in `backend/alembic` with config file `backend/alembic.ini`.

Run commands from repo root or inside `backend/`:

```bash
# Apply latest migrations
DB_URL=postgresql+psycopg://gst_user:gst_password_2023@localhost:5432/gst_service_center \
	alembic -c backend/alembic.ini upgrade head

# Create a new revision (autogenerate)
alembic -c backend/alembic.ini revision -m "add feature xyz" --autogenerate
```

Makefile helpers (inside `backend/`):

```bash
make migrate            # upgrade head
make revision MSG="add widget table"  # new revision
make stamp              # stamp current head (use with caution)
```

### URL Conventions

- Runtime async app URL uses `postgresql+asyncpg://...`
- Alembic auto-converts async URL to sync `postgresql+psycopg://` for migrations.

### Soft Delete Support

`invoices.is_deleted` added in revision `20250924_0002` (soft delete). Queries in runtime filter out deleted invoices at the service/router layer.

## Testing

### Modes

There are two primary test execution modes:

1. FAST_TESTS=1 (default in `make test`):

   - Uses a lightweight SQLite file database (`fasttests.db`).
   - Skips expensive startup tasks (observability init, DB health check, seed routines) via a fast-path in `lifespan`.
   - Reduces bcrypt rounds (env `BCRYPT_ROUNDS`, default 4 in tests) for faster auth hashing.
   - Provides a shortcut auth token in `auth_client` fixture to avoid hashing/login route cost.

2. Normal mode (no FAST_TESTS):
   - Runs closer to production settings (full startup, standard bcrypt cost).
   - Use `make test-normal` to exercise this path.

### Targets

Inside `backend/Makefile`:

```
make test         # fast mode, excludes performance tests
make test-normal  # normal mode run
make contract     # contract tests subset
make integration  # integration tests subset
make unit         # unit tests subset
make test-all     # includes performance tests
make cov-html     # generate/open HTML coverage report
```

### Fixture Stability

The test suite previously experienced teardown hangs due to overlapping async DB session fixtures. This was resolved by unifying into a single `db_session` fixture providing:

- Simple `AsyncSessionLocal` path for FAST_TESTS (SQLite)
- SAVEPOINT-wrapped transaction rollback for Postgres (when `TEST_DB_URL` is set)

Future Postgres-backed test runs can enable parity by exporting `TEST_DB_URL` and invoking `make test-postgres`.

## Next Improvements

- Remove legacy `create_database_tables_async()` from startup once all environments use migrations.
- Introduce migration-based test fixture.
- Add additional schema features (invoice numbering, constraints, etc.).

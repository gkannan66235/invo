import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Add backend/src to import path (env.py lives in backend/alembic)
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC_DIR = os.path.join(BACKEND_DIR, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models metadata
"""Alembic environment script.

This version deliberately avoids importing the runtime database configuration
module that creates engines and sessions. We only need model metadata and a
database URL. The URL is resolved from environment variables with the
following precedence:

1. DB_URL
2. DATABASE_URL
3. Built-in default (local Postgres) if neither provided

If an async driver URL is supplied (e.g. postgresql+asyncpg://) it is converted
to a synchronous driver for Alembic operations.
"""

from src.models.database import Base  # noqa: E402

target_metadata = Base.metadata

# Resolve database URL precedence:
# 1. Explicit env override: DB_URL or DATABASE_URL
# 2. Value already present in ini via %(DB_URL)s substitution (if provided)
# 3. Application config (db_config.database_url)
env_override = os.getenv('DB_URL') or os.getenv('DATABASE_URL')
# In testing, allow TEST_DB_URL to override (higher fidelity Postgres test database)
if os.getenv('TESTING', 'false').lower() == 'true' and os.getenv('TEST_DB_URL'):
    env_override = os.getenv('TEST_DB_URL')
if env_override:
    raw_url = env_override
else:
    ini_url = config.get_main_option('sqlalchemy.url')
    if ini_url and ini_url not in ('', '%(DB_URL)s'):
        raw_url = ini_url
    else:
        # Fallback default (mirrors runtime default but simplified)
        user = os.getenv('DB_USER', 'postgres')
        password = os.getenv('DB_PASSWORD', 'postgres')
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        name = os.getenv('DB_NAME', 'invoice_system')
        # Use psycopg (v3) driver which is installed; avoids psycopg2 dependency
        raw_url = f'postgresql+psycopg://{user}:{password}@{host}:{port}/{name}'

# Convert any Postgres URL to pg8000 (pure Python) for Alembic to avoid system selector issues
if raw_url.startswith('postgresql+asyncpg://'):
    raw_url = raw_url.replace('postgresql+asyncpg://',
                              'postgresql+pg8000://', 1)
elif raw_url.startswith('postgresql+psycopg://'):
    raw_url = raw_url.replace('postgresql+psycopg://',
                              'postgresql+pg8000://', 1)
elif raw_url.startswith('postgresql://') and '+pg8000' not in raw_url:
    raw_url = raw_url.replace('postgresql://', 'postgresql+pg8000://', 1)

config.set_main_option('sqlalchemy.url', raw_url)


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

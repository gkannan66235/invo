import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Add backend src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models metadata
from src.models.database import Base  # noqa: E402
from src.config.database import db_config  # noqa: E402

target_metadata = Base.metadata

# Override database URL from environment / existing config
raw_url = db_config.database_url
if raw_url.startswith("postgresql+asyncpg://"):
    sync_url = raw_url.replace("postgresql+asyncpg://", "postgresql://", 1)
else:
    sync_url = raw_url
config.set_main_option('sqlalchemy.url', sync_url)


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

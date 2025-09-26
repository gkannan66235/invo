"""Utility script to run Alembic migrations programmatically before app start (optional).

Usage:
    python run_migrations.py

This can be invoked in container entrypoint before launching uvicorn.
"""
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect
import os

BASE_DIR = os.path.dirname(__file__)
ALEMBIC_INI = os.path.join(BASE_DIR, 'alembic.ini')
BASELINE_REVISION = '20250924_0001'


def run():
    cfg = Config(ALEMBIC_INI)
    # Support overriding via DB_URL or DATABASE_URL (DB_URL aligns with alembic.ini placeholder)
    override = os.getenv('DB_URL') or os.getenv('DATABASE_URL')
    if override:
        cfg.set_main_option('sqlalchemy.url', override)
    # Auto-stamp baseline if tables already exist (legacy bootstrapped schema)
    url = cfg.get_main_option('sqlalchemy.url')
    if url.startswith('postgresql+asyncpg://'):
        url = url.replace('postgresql+asyncpg://', 'postgresql+psycopg://', 1)
    try:
        engine = create_engine(url)
        insp = inspect(engine)
        existing_tables = set(insp.get_table_names())
        if 'alembic_version' not in existing_tables:
            sentinel_tables = {'roles', 'users', 'customers', 'invoices'}
            if existing_tables & sentinel_tables:
                print(
                    f"[migrations] Existing tables detected without alembic_version. Stamping baseline {BASELINE_REVISION}.")
                command.stamp(cfg, BASELINE_REVISION)
    except Exception as e:
        print(f"[migrations] Warning: baseline detection failed: {e}")

    command.upgrade(cfg, 'head')


if __name__ == '__main__':
    run()
